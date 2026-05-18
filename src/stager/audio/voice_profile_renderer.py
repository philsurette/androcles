from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import subprocess
from typing import Protocol

from stager.audio.ffmpeg_filter_graph import FfmpegFilterGraphCompiler
from stager.audio.voice_profile_resolver import ResolvedVoiceProfile
from stager.audio.voice_render_cache import VoiceRenderCache, VoiceRenderSegment, VoiceRenderSource
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation, FfmpegProbe


logger = logging.getLogger(__name__)


class CommandRunner(Protocol):
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        ...


@dataclass(frozen=True)
class VoiceRenderResult:
    segment: VoiceRenderSegment
    manifest_path: Path
    rendered: bool
    cache_hit: bool
    command: tuple[str, ...] = ()


@dataclass
class VoiceProfileRenderer:
    paths_config: paths.PathConfig
    installation: FfmpegInstallation | None = None
    command_runner: CommandRunner = subprocess.run
    compiler: FfmpegFilterGraphCompiler = field(default_factory=FfmpegFilterGraphCompiler)
    tail_padding_seconds: float = 2.0

    def render_segment(
        self,
        *,
        resolved_profile: ResolvedVoiceProfile,
        source: VoiceRenderSource,
        segment_id: str,
        force: bool = False,
        output_format: str = "wav",
        production_id: str | None = None,
        production_content_hash: str | None = None,
    ) -> VoiceRenderResult:
        installation = self._installation()
        cache = VoiceRenderCache(self.paths_config)
        renderer_capabilities = {name: installation.has_filter(name) for name in sorted(installation.filters)}
        segment = cache.segment(
            resolved_profile=resolved_profile,
            source=source,
            segment_id=segment_id,
            renderer_backend="ffmpeg",
            renderer_capabilities=renderer_capabilities,
            output_format=output_format,
            production_id=production_id,
            production_content_hash=production_content_hash,
        )
        if cache.is_hit(segment) and not force:
            logger.info("Voice render cache hit: %s", paths.display_path(segment.output_path))
            manifest_path = cache.manifest_path(cache.render_profile_id(resolved_profile))
            return VoiceRenderResult(segment=segment, manifest_path=manifest_path, rendered=False, cache_hit=True)

        filter_spec = self._filter_spec(resolved_profile)
        segment.output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(installation.ffmpeg_path),
            "-y",
            "-hide_banner",
            "-i",
            str(source.path),
            "-af",
            filter_spec,
            str(segment.output_path),
        ]
        result = self.command_runner(command, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or "").strip()
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"Voice profile FFmpeg render failed for {paths.display_path(source.path)}{suffix}")
        if not segment.output_path.exists():
            raise RuntimeError(f"Voice profile render did not create {paths.display_path(segment.output_path)}")
        manifest_path = cache.write_manifest(
            resolved_profile=resolved_profile,
            renderer_backend="ffmpeg",
            renderer_capabilities=renderer_capabilities,
            segments=(segment,),
            output_format=output_format,
        )
        logger.info("Rendered voice-profile audio: %s", paths.display_path(segment.output_path))
        return VoiceRenderResult(
            segment=segment,
            manifest_path=manifest_path,
            rendered=True,
            cache_hit=False,
            command=tuple(command),
        )

    def _filter_spec(self, resolved_profile: ResolvedVoiceProfile) -> str:
        graph = self.compiler.compile(resolved_profile.transforms)
        filters = list(graph.filters)
        if any(transform.type in {"reverb", "delay"} for transform in resolved_profile.transforms):
            filters.append(f"apad=pad_dur={self.tail_padding_seconds}")
        if not filters:
            filters.append("anull")
        return ",".join(filters)

    def _installation(self) -> FfmpegInstallation:
        if self.installation is not None:
            missing = self.installation.missing_required_voice_profile_filters()
            if missing:
                raise RuntimeError(f"Missing required FFmpeg voice-profile filter(s): {', '.join(missing)}")
            return self.installation
        installation = FfmpegProbe(working_dir=paths.project_root()).find_installation()
        missing = installation.missing_required_voice_profile_filters()
        if missing:
            raise RuntimeError(f"Missing required FFmpeg voice-profile filter(s): {', '.join(missing)}")
        self.installation = installation
        return installation
