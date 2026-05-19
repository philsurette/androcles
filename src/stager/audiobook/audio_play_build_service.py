"""Service for building assembled audioplay output."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from stager.audio.segment_build_service import SegmentBuildService
from stager.audio.voice_profile_config import VoiceProfileConfig
from stager.audio.voice_profile_cast import VoiceProfileCastResolver
from stager.audio.voice_profile_renderer import CommandRunner, VoiceProfileRenderer, VoiceRenderResult
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.audio.voice_render_cache import VoiceRenderCache
from stager.audiobook.play_builder import PlayBuilder
from stager.domain.play import Play
from stager.loudnorm.normalizer import Normalizer
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.shared import paths as path_display
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.shared.ffmpeg_probe import FfmpegInstallation
from stager.shared.paths import PathConfig
from stager.shared.progress_reporter import ProgressReporter
from stager.text.text_artifact_builder import TextArtifactBuilder


logger = logging.getLogger(__name__)


@dataclass
class AudioPlayBuildService:
    """Build audioplay media and optional normalized copies."""

    paths: PathConfig
    progress_reporter: ProgressReporter | None = None
    command_runner: CommandRunner | None = None
    ffmpeg_installation: FfmpegInstallation | None = None

    def build(
        self,
        *,
        part: str | None = None,
        segment_spacing_ms: int = 500,
        callouts: bool = True,
        callout_spacing_ms: int = 125,
        minimal_callouts: bool = True,
        captions: bool = True,
        generate_audio: bool = True,
        librivox: bool | None = None,
        audio_format: str = "mp4",
        normalize_output: bool = True,
        prepare: bool = True,
        audio_source: str = "auto",
        voice_profiles: bool = False,
        voice_actor: str | None = None,
    ):
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths,
            librivox_override=librivox,
        ).resolve()
        effective_librivox = effective_build_type == "librivox"
        play: Play = ProductionPlayLoader(paths_config=self.paths).load()
        output_count = self._output_count(play, part=part, librivox=effective_librivox)
        progress_total = output_count
        if prepare:
            progress_total += 1
        if normalize_output and generate_audio:
            progress_total += output_count
        if self.progress_reporter is not None:
            description = "Preparing audioplay" if prepare else "Rendering audioplay"
            self.progress_reporter.start(progress_total, description)
        if prepare:
            logger.info("Preparing text artifacts and split segments before audioplay")
            TextArtifactBuilder(paths=self.paths).build_all(line_no_prefix=True, build_type=effective_build_type)
            SegmentBuildService(paths=self.paths).build(build_type=effective_build_type)
            if self.progress_reporter is not None:
                self.progress_reporter.advance("Rendering audioplay")
        if part is None:
            part_no = None
        else:
            part_no = int(part)
        if voice_profiles:
            self._render_voice_profiles(
                role=None,
                actor=voice_actor,
                audio_source=audio_source,
            )

        builder = PlayBuilder(
            spacing_ms=segment_spacing_ms,
            include_callouts=callouts,
            callout_spacing_ms=callout_spacing_ms,
            minimal_callouts=minimal_callouts,
            audio_format=audio_format,
            part_gap_ms=2000,
            generate_audio=generate_audio,
            generate_captions=captions,
            librivox=effective_librivox,
            audio_source=audio_source,
            voice_profiles=voice_profiles,
            voice_actor=voice_actor,
            play=play,
            paths=self.paths,
            progress_reporter=self.progress_reporter,
        )
        out_paths = builder.build_audio(part_no=part_no)
        if normalize_output and generate_audio:
            normalizer = Normalizer()
            for out_path in out_paths:
                target_dir = out_path.parent / "normalized"
                target_dir.mkdir(parents=True, exist_ok=True)
                norm_path = target_dir / out_path.name
                logger.info("Normalizing audioplay to %s", path_display.display_path(norm_path))
                normalizer.normalize(str(out_path), str(norm_path))
                if self.progress_reporter is not None:
                    self.progress_reporter.advance(f"Normalized {out_path.name}")
        elif normalize_output and not generate_audio:
            logger.info("Skipping normalization because audio rendering was skipped.")
        if self.progress_reporter is not None:
            self.progress_reporter.finish("Built audioplay")
        return out_paths

    def _render_voice_profiles(
        self,
        *,
        role: str | None,
        actor: str | None,
        audio_source: str,
    ) -> tuple[VoiceRenderResult, ...]:
        from stager.audio.cleaned_audio_selector import CleanedAudioSelector, AUDIO_SOURCE_CANONICAL

        config = VoiceProfileConfig.load(self.paths)
        if not config.cast_profiles:
            return ()
        resolver = VoiceProfileResolver(config)
        cast_resolver = VoiceProfileCastResolver(self.paths)
        cache = VoiceRenderCache(self.paths)
        selector = CleanedAudioSelector(paths_config=self.paths, audio_source=audio_source)
        renderer = VoiceProfileRenderer(
            paths_config=self.paths,
            installation=self.ffmpeg_installation,
            **({"command_runner": self.command_runner} if self.command_runner is not None else {}),
        )
        roles = [role] if role is not None else sorted({profile.role for profile in config.cast_profiles.values()})
        results = []
        for candidate_role in roles:
            resolved = resolver.resolve(candidate_role, actor=cast_resolver.actor_for_role(candidate_role, actor))
            if resolved is None:
                continue
            role_dir = self.paths.segments_dir / resolved.role
            if not role_dir.exists():
                continue
            for canonical_path in sorted(role_dir.glob("*.wav")):
                selected_path = selector.segment_path(resolved.role, canonical_path.stem)
                is_cleaned = selected_path != canonical_path and audio_source != AUDIO_SOURCE_CANONICAL
                source = cache.source_identity(
                    layer="cleaned" if is_cleaned else "canonical",
                    path=selected_path,
                    cleanup_review_id="cleanup_review" if is_cleaned else None,
                    cleanup_review_path=(
                        self.paths.audio_out_dir / "cleaned" / "cleanup_review.json" if is_cleaned else None
                    ),
                )
                results.append(
                    renderer.render_segment(
                        resolved_profile=resolved,
                        source=source,
                        segment_id=canonical_path.stem,
                    )
                )
        return tuple(results)

    def _output_count(self, play: Play, *, part: str | None, librivox: bool) -> int:
        if librivox:
            return len([candidate for candidate in play.parts if candidate.part_no is not None])
        return 1
