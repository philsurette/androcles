from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stager.audio.audio_cleanup_analyzer import AudioCleanupAnalysisStore, AudioCleanupAnalyzer
from stager.audio.audio_cleanup_config import AudioCleanupConfig
from stager.audio.audio_cleanup_filter_graph import AudioCleanupFilterGraphCompiler
from stager.audio.audio_cleanup_renderer import AudioCleanupRenderer
from stager.shared import paths
from stager.shared.external_tool_checker import ExternalToolChecker
from stager.shared.ffmpeg_probe import FfmpegInstallation


@dataclass(frozen=True)
class AudioCleanupPlanEntry:
    role: str
    resolution: str
    profile: str | None
    filters: tuple[str, ...]
    missing_optional_filters: tuple[str, ...]


@dataclass(frozen=True)
class AudioCleanupPlan:
    config_path: str
    cleanup_approach: str
    default_profile: str
    batch_padding_seconds: float
    boundary_warning_ms: int
    entries: tuple[AudioCleanupPlanEntry, ...]


@dataclass(frozen=True)
class AudioCleanupAnalysisResult:
    json_path: Path
    markdown_path: Path
    entry_count: int


@dataclass(frozen=True)
class PreparedAudioCleanupBatchResult:
    batch_id: str
    manifest_path: Path
    segment_count: int
    cache_hit: bool
    warning_count: int


@dataclass(frozen=True)
class RenderedAudioCleanupBatchResult:
    batch_id: str
    manifest_path: Path
    rendered_count: int
    warning_count: int


@dataclass
class AudioCleanupService:
    paths_config: paths.PathConfig
    tool_checker: ExternalToolChecker | None = None

    def load_config(self) -> AudioCleanupConfig:
        return AudioCleanupConfig.load(self.paths_config)

    def capability_report(self) -> list[str]:
        installation = self._installation()
        lines = [
            f"ffmpeg: {paths.display_path(installation.ffmpeg_path)}",
            f"ffprobe: {paths.display_path(installation.ffprobe_path)}",
            f"source: {installation.source}",
        ]
        if installation.config_path is not None:
            lines.append(f"config: {paths.display_path(installation.config_path)}")
        missing_required = installation.missing_required_audio_cleanup_filters()
        if missing_required:
            lines.append(f"missing required cleanup filters: {', '.join(missing_required)}")
        else:
            lines.append("required cleanup filters: found")
        optional = installation.optional_audio_cleanup_filter_report()
        found_optional = [name for name, found in optional.items() if found]
        missing_optional = [name for name, found in optional.items() if not found]
        lines.append(f"optional cleanup filters found: {', '.join(found_optional) if found_optional else 'none'}")
        lines.append(f"optional cleanup filters missing: {', '.join(missing_optional) if missing_optional else 'none'}")
        return lines

    def build_plan(
        self,
        *,
        role: str | None = None,
        profile: str | None = None,
        use_analysis: bool = False,
    ) -> AudioCleanupPlan:
        config = self.load_config()
        roles = [role] if role else self._roles(config)
        installation = self._installation()
        compiler = AudioCleanupFilterGraphCompiler(available_filters=set(installation.filters))
        analysis_store = AudioCleanupAnalysisStore(self.paths_config)
        entries = []
        for role_name in roles:
            resolution = config.resolve_role(role_name)
            if use_analysis:
                analysis_store.require_role(role_name)
                resolution_name = "analysis"
                profile_name = None
                filters: tuple[str, ...] = ()
                missing: tuple[str, ...] = ()
            elif profile is not None:
                selected_profile = config.profiles.get(profile)
                if selected_profile is None:
                    raise RuntimeError(f"Unknown audio cleanup profile {profile!r}")
                compiled = compiler.compile(selected_profile)
                resolution_name = "profile"
                profile_name = selected_profile.name
                filters = compiled.filters
                missing = compiled.missing_optional_filters
            elif resolution.uses_analysis:
                analysis_store.require_role(role_name)
                resolution_name = "analysis"
                profile_name = None
                filters = ()
                missing = ()
            elif resolution.disabled:
                resolution_name = "none"
                profile_name = None
                filters = ()
                missing = ()
            else:
                if resolution.profile is None:
                    raise RuntimeError(f"Role {role_name} did not resolve to a cleanup profile")
                compiled = compiler.compile(resolution.profile)
                resolution_name = "profile"
                profile_name = resolution.profile.name
                filters = compiled.filters
                missing = compiled.missing_optional_filters
            entries.append(
                AudioCleanupPlanEntry(
                    role=role_name,
                    resolution=resolution_name,
                    profile=profile_name,
                    filters=filters,
                    missing_optional_filters=missing,
                )
            )
        return AudioCleanupPlan(
            config_path=paths.display_path(self.paths_config.play_dir / "audio_cleanup.yaml"),
            cleanup_approach=config.cleanup_approach,
            default_profile=config.default_profile,
            batch_padding_seconds=config.batch_padding_seconds,
            boundary_warning_ms=config.boundary_warning_ms,
            entries=tuple(entries),
        )

    def analyze(self, *, role: str | None = None) -> AudioCleanupAnalysisResult:
        analyzer = AudioCleanupAnalyzer(paths_config=self.paths_config)
        report = analyzer.analyze(role=role)
        json_path, markdown_path = analyzer.write_report(report)
        return AudioCleanupAnalysisResult(
            json_path=json_path,
            markdown_path=markdown_path,
            entry_count=len(report.entries),
        )

    def prepare(
        self,
        *,
        role: str | None = None,
        profile: str | None = None,
        use_analysis: bool = False,
    ) -> tuple[PreparedAudioCleanupBatchResult, ...]:
        plan = self.build_plan(role=role, profile=profile, use_analysis=use_analysis)
        renderer = AudioCleanupRenderer(paths_config=self.paths_config)
        results = []
        for entry in plan.entries:
            if entry.resolution == "none":
                continue
            segment_paths = self._segment_paths(entry.role)
            if not segment_paths:
                continue
            batch_id = self._batch_id(entry)
            prepared = renderer.prepare_batch(
                batch_id=batch_id,
                segment_paths=segment_paths,
                padding_seconds=plan.batch_padding_seconds,
                boundary_warning_ms=plan.boundary_warning_ms,
                resolved_filters=entry.filters,
            )
            warning_count = sum(1 for boundary in prepared.manifest.cleaned_boundaries if boundary.warnings)
            results.append(
                PreparedAudioCleanupBatchResult(
                    batch_id=batch_id,
                    manifest_path=prepared.manifest_path,
                    segment_count=len(prepared.manifest.segments),
                    cache_hit=prepared.cache_hit,
                    warning_count=warning_count,
                )
            )
        return tuple(results)

    def render(
        self,
        *,
        role: str | None = None,
        profile: str | None = None,
        use_analysis: bool = False,
    ) -> tuple[RenderedAudioCleanupBatchResult, ...]:
        plan = self.build_plan(role=role, profile=profile, use_analysis=use_analysis)
        renderer = AudioCleanupRenderer(paths_config=self.paths_config)
        results = []
        for entry in plan.entries:
            if entry.resolution == "none":
                continue
            segment_paths = self._segment_paths(entry.role)
            if not segment_paths:
                continue
            batch_id = self._batch_id(entry)
            rendered = renderer.render_batch(
                batch_id=batch_id,
                segment_paths=segment_paths,
                padding_seconds=plan.batch_padding_seconds,
                boundary_warning_ms=plan.boundary_warning_ms,
                resolved_filters=entry.filters,
            )
            results.append(
                RenderedAudioCleanupBatchResult(
                    batch_id=batch_id,
                    manifest_path=rendered.manifest_path,
                    rendered_count=rendered.rendered_count,
                    warning_count=rendered.warning_count,
                )
            )
        return tuple(results)

    def _installation(self) -> FfmpegInstallation:
        checker = self.tool_checker or ExternalToolChecker()
        return checker.require_audio_tools()

    def _roles(self, config: AudioCleanupConfig) -> list[str]:
        roles = set(config.roles)
        if self.paths_config.segments_dir.exists():
            roles.update(path.name for path in self.paths_config.segments_dir.iterdir() if path.is_dir())
        return sorted(roles)

    def _segment_paths(self, role: str) -> list[Path]:
        role_dir = self.paths_config.segments_dir / role
        return sorted(role_dir.glob("*.wav")) if role_dir.exists() else []

    def _batch_id(self, entry: AudioCleanupPlanEntry) -> str:
        profile = entry.profile or entry.resolution
        return f"{entry.role}-{profile}".replace("/", "_").replace(" ", "_")
