from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stager.audio.audio_cleanup_service import (
    AudioCleanupAnalysisResult,
    AudioCleanupPlan,
    AudioCleanupService,
    PreparedAudioCleanupBatchResult,
    RenderedAudioCleanupBatchResult,
)
from stager.audio.cleaned_audio_selector import AUDIO_SOURCE_CANONICAL, CleanedAudioSelector, SUPPORTED_AUDIO_SOURCES
from stager.audio.voice_profile_config import VoiceProfileConfig
from stager.audio.voice_profile_renderer import VoiceProfileRenderer, VoiceRenderResult
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.audio.voice_render_cache import VoiceRenderCache
from stager.audiobook.audio_play_build_service import AudioPlayBuildService
from stager.domain.play import Play
from stager.playbook.playbook_builder import PlaybookBuilder
from stager.production.production_status import ProductionStatus, ProductionStatusService
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.shared.external_tool_checker import ExternalToolChecker
from stager.shared import paths
from stager.staging.export_service import StagingExportService


@dataclass(frozen=True)
class PrepareAudioResult:
    status: ProductionStatus
    cleanup_plan: AudioCleanupPlan
    cleanup_analysis: AudioCleanupAnalysisResult | None
    prepared_batches: tuple[PreparedAudioCleanupBatchResult, ...]
    rendered_batches: tuple[RenderedAudioCleanupBatchResult, ...]
    voice_profile_count: int
    voice_results: tuple[VoiceRenderResult, ...]
    dry_run: bool


@dataclass(frozen=True)
class OutputBuildResult:
    paths: tuple[Path, ...]
    production_version: str | None
    production_source: str | None
    audio_source: str


class AudioOutputWorkflowService:
    def __init__(
        self,
        *,
        paths_config: paths.PathConfig,
        play: Play,
        tool_checker: ExternalToolChecker | None = None,
    ) -> None:
        self.paths_config = paths_config
        self.play = play
        self.tool_checker = tool_checker or ExternalToolChecker()

    def prepare_audio(
        self,
        *,
        role: str | None = None,
        profile: str | None = None,
        use_analysis: bool = False,
        run: bool = False,
        force: bool = False,
        audio_source: str = "auto",
        voice_actor: str | None = None,
    ) -> PrepareAudioResult:
        self._validate_audio_source(audio_source)
        cleanup = AudioCleanupService(paths_config=self.paths_config, tool_checker=self.tool_checker)
        status = ProductionStatusService(paths_config=self.paths_config, play=self.play).build()
        cleanup_analysis = cleanup.analyze(role=role) if run and use_analysis else None
        cleanup_plan = cleanup.build_plan(role=role, profile=profile, use_analysis=use_analysis)
        voice_profile_count = len(VoiceProfileConfig.load(self.paths_config).cast_profiles)
        if not run:
            return PrepareAudioResult(
                status=status,
                cleanup_plan=cleanup_plan,
                cleanup_analysis=None,
                prepared_batches=(),
                rendered_batches=(),
                voice_profile_count=voice_profile_count,
                voice_results=(),
                dry_run=True,
            )

        prepared_batches = tuple(cleanup.prepare(role=role, profile=profile, use_analysis=use_analysis))
        rendered_batches = tuple(cleanup.render(role=role, profile=profile, use_analysis=use_analysis, force=force))
        voice_results = self._render_voice_profiles(
            role=role,
            actor=voice_actor,
            audio_source=audio_source,
            force=force,
        )
        return PrepareAudioResult(
            status=status,
            cleanup_plan=cleanup_plan,
            cleanup_analysis=cleanup_analysis,
            prepared_batches=prepared_batches,
            rendered_batches=rendered_batches,
            voice_profile_count=voice_profile_count,
            voice_results=voice_results,
            dry_run=False,
        )

    def build_playbook(
        self,
        *,
        build_type: str | None = None,
        audio_format: str = "wav",
        audio_source: str = "auto",
        voice_profiles: bool = False,
        voice_actor: str | None = None,
        staging: bool = True,
        blocking_diagrams: bool = True,
    ) -> OutputBuildResult:
        if audio_format not in ("wav", "mp3"):
            raise RuntimeError("audio-format must be one of: wav, mp3")
        self._validate_audio_source(audio_source)
        if staging:
            StagingExportService(paths_config=self.paths_config).export()
        installation = self.tool_checker.require_audio_tools() if audio_format == "mp3" or voice_profiles else None
        if voice_profiles:
            self._render_voice_profiles(actor=voice_actor, audio_source=audio_source, installation=installation)
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths_config,
            explicit_build_type=build_type,
        ).resolve()
        zip_path = PlaybookBuilder(
            play=self.play,
            paths=self.paths_config,
            build_type=effective_build_type,
            audio_format=audio_format,
            audio_source=audio_source,
            voice_profiles=voice_profiles,
            voice_actor=voice_actor,
            blocking_diagrams=blocking_diagrams and staging,
        ).build()
        status = ProductionStatusService(paths_config=self.paths_config, play=self.play).build()
        return OutputBuildResult(
            paths=(zip_path,),
            production_version=status.playbook.production_version,
            production_source=status.playbook.production_source,
            audio_source=audio_source,
        )

    def build_audioplay(
        self,
        *,
        part: str | None = None,
        audio_format: str = "mp4",
        audio_source: str = "auto",
        voice_profiles: bool = False,
        voice_actor: str | None = None,
        normalize_output: bool = True,
        prepare: bool = True,
        staging: bool = True,
    ) -> OutputBuildResult:
        if audio_format not in ("mp4", "mp3", "wav"):
            raise RuntimeError("audio-format must be one of: mp4, mp3, wav")
        self._validate_audio_source(audio_source)
        if staging:
            StagingExportService(paths_config=self.paths_config).export()
        installation = self.tool_checker.require_audio_tools()
        out_paths = tuple(
            AudioPlayBuildService(
                paths=self.paths_config,
                ffmpeg_installation=installation,
            ).build(
                part=part,
                audio_format=audio_format,
                audio_source=audio_source,
                voice_profiles=voice_profiles,
                voice_actor=voice_actor,
                normalize_output=normalize_output,
                prepare=prepare,
            )
        )
        status = ProductionStatusService(paths_config=self.paths_config, play=self.play).build()
        return OutputBuildResult(
            paths=out_paths,
            production_version=status.working_production_version or status.current_published_version,
            production_source=None,
            audio_source=audio_source,
        )

    def _render_voice_profiles(
        self,
        *,
        role: str | None = None,
        actor: str | None = None,
        audio_source: str = "auto",
        force: bool = False,
        installation=None,
    ) -> tuple[VoiceRenderResult, ...]:
        config = VoiceProfileConfig.load(self.paths_config)
        if not config.cast_profiles:
            return ()
        active_installation = installation or self.tool_checker.require_audio_tools()
        missing_filters = active_installation.missing_required_voice_profile_filters()
        if missing_filters:
            raise RuntimeError(f"Missing required FFmpeg voice-profile filter(s): {', '.join(missing_filters)}")
        resolver = VoiceProfileResolver(config)
        cache = VoiceRenderCache(self.paths_config)
        selector = CleanedAudioSelector(paths_config=self.paths_config, audio_source=audio_source)
        renderer = VoiceProfileRenderer(paths_config=self.paths_config, installation=active_installation)
        roles = [role] if role is not None else sorted({profile.role for profile in config.cast_profiles.values()})
        results = []
        for candidate_role in roles:
            resolved = resolver.resolve(candidate_role, actor=actor)
            if resolved is None:
                continue
            role_dir = self.paths_config.segments_dir / resolved.role
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
                        self.paths_config.audio_out_dir / "cleaned" / "cleanup_review.json" if is_cleaned else None
                    ),
                )
                results.append(
                    renderer.render_segment(
                        resolved_profile=resolved,
                        source=source,
                        segment_id=canonical_path.stem,
                        force=force,
                    )
                )
        return tuple(results)

    def _validate_audio_source(self, audio_source: str) -> None:
        if audio_source not in SUPPORTED_AUDIO_SOURCES:
            raise RuntimeError("audio-source must be one of: auto, canonical, cleaned")
