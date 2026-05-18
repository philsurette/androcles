from __future__ import annotations

from dataclasses import dataclass
import json
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
    loudnorm_profile: str
    missing_optional_filters: tuple[str, ...]
    duration_preserving: bool = True


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
                loudnorm_profile = "none"
                missing: tuple[str, ...] = ()
                duration_preserving = True
            elif profile is not None:
                selected_profile = config.profiles.get(profile)
                if selected_profile is None:
                    raise RuntimeError(f"Unknown audio cleanup profile {profile!r}")
                compiled = compiler.compile(selected_profile)
                resolution_name = "profile"
                profile_name = selected_profile.name
                filters = compiled.filters
                loudnorm_profile = selected_profile.loudnorm
                missing = compiled.missing_optional_filters
                duration_preserving = compiled.duration_preserving
            elif resolution.uses_analysis:
                analysis_store.require_role(role_name)
                resolution_name = "analysis"
                profile_name = None
                filters = ()
                loudnorm_profile = "none"
                missing = ()
                duration_preserving = True
            elif resolution.disabled:
                resolution_name = "none"
                profile_name = None
                filters = ()
                loudnorm_profile = "none"
                missing = ()
                duration_preserving = True
            else:
                if resolution.profile is None:
                    raise RuntimeError(f"Role {role_name} did not resolve to a cleanup profile")
                compiled = compiler.compile(resolution.profile)
                resolution_name = "profile"
                profile_name = resolution.profile.name
                filters = compiled.filters
                loudnorm_profile = resolution.profile.loudnorm
                missing = compiled.missing_optional_filters
                duration_preserving = compiled.duration_preserving
            entries.append(
                AudioCleanupPlanEntry(
                    role=role_name,
                    resolution=resolution_name,
                    profile=profile_name,
                    filters=filters,
                    loudnorm_profile=loudnorm_profile,
                    missing_optional_filters=missing,
                    duration_preserving=duration_preserving,
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
            if not entry.duration_preserving:
                raise RuntimeError(f"Audio cleanup batch {entry.role} uses a non-duration-preserving filter chain")
            for group in self._segment_groups(entry.role):
                batch_id = self._batch_id(entry, floor_noise_id=group.floor_noise_id)
                prepared = renderer.prepare_batch(
                    batch_id=batch_id,
                    segment_paths=group.segment_paths,
                    padding_seconds=plan.batch_padding_seconds,
                    boundary_warning_ms=plan.boundary_warning_ms,
                    resolved_filters=entry.filters,
                    loudnorm_profile=entry.loudnorm_profile,
                    floor_noise_path=group.floor_noise_path,
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
            if not entry.duration_preserving:
                raise RuntimeError(f"Audio cleanup batch {entry.role} uses a non-duration-preserving filter chain")
            for group in self._segment_groups(entry.role):
                batch_id = self._batch_id(entry, floor_noise_id=group.floor_noise_id)
                rendered = renderer.render_batch(
                    batch_id=batch_id,
                    segment_paths=group.segment_paths,
                    padding_seconds=plan.batch_padding_seconds,
                    boundary_warning_ms=plan.boundary_warning_ms,
                    resolved_filters=entry.filters,
                    loudnorm_profile=entry.loudnorm_profile,
                    floor_noise_path=group.floor_noise_path,
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

    def _segment_groups(self, role: str) -> tuple["AudioCleanupSegmentGroup", ...]:
        floor_noise = self._floor_noise_index()
        groups: dict[tuple[str | None, Path | None], list[Path]] = {}
        for segment_path in self._segment_paths(role):
            key = floor_noise.get((role, segment_path.stem), (None, None))
            groups.setdefault(key, []).append(segment_path)
        return tuple(
            AudioCleanupSegmentGroup(
                floor_noise_id=floor_noise_id,
                floor_noise_path=floor_noise_path,
                segment_paths=tuple(sorted(segment_paths)),
            )
            for (floor_noise_id, floor_noise_path), segment_paths in sorted(
                groups.items(),
                key=lambda item: item[0][0] or "",
            )
        )

    def _floor_noise_index(self) -> dict[tuple[str, str], tuple[str | None, Path | None]]:
        imports_dir = self.paths_config.build_dir / "linerecorder" / "imports"
        if not imports_dir.exists():
            return {}
        index: dict[tuple[str, str], tuple[str | None, Path | None]] = {}
        for import_json in sorted(imports_dir.glob("*/import.json")):
            try:
                data = json.loads(import_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            role = data.get("role_id")
            if not isinstance(role, str):
                continue
            floor_noise_items = self._floor_noise_items(data, import_json.parent)
            for imported in data.get("imported", []):
                if not isinstance(imported, dict):
                    continue
                segment_id = imported.get("segment_id")
                if not isinstance(segment_id, str):
                    continue
                floor_noise_id, floor_noise_path = self._resolve_floor_noise(imported, floor_noise_items)
                index[(role, segment_id)] = (floor_noise_id, floor_noise_path)
        return index

    def _floor_noise_items(
        self,
        transaction: dict,
        transaction_dir: Path,
    ) -> list["ImportedFloorNoise"]:
        items = []
        for floor_noise in transaction.get("floor_noise_recordings", []) or []:
            if not isinstance(floor_noise, dict):
                continue
            floor_noise_id = floor_noise.get("id")
            recorded_at = floor_noise.get("recorded_at")
            if not isinstance(floor_noise_id, str) or not isinstance(recorded_at, str):
                continue
            artifact_path = self._artifact_path(floor_noise.get("artifact_path"))
            if artifact_path is None:
                artifact_path = self._floor_noise_path(transaction_dir, floor_noise_id)
            items.append(
                ImportedFloorNoise(
                    id=floor_noise_id,
                    recorded_at=recorded_at,
                    artifact_path=artifact_path,
                )
            )
        return sorted(items, key=lambda item: item.recorded_at)

    def _resolve_floor_noise(
        self,
        imported: dict,
        floor_noise_items: list["ImportedFloorNoise"],
    ) -> tuple[str | None, Path | None]:
        floor_noise_id = imported.get("floor_noise_id")
        if isinstance(floor_noise_id, str):
            for floor_noise in floor_noise_items:
                if floor_noise.id == floor_noise_id:
                    return floor_noise.id, floor_noise.artifact_path
            return floor_noise_id, None
        recorded_at = imported.get("recorded_at")
        if not isinstance(recorded_at, str):
            return None, None
        candidates = [floor_noise for floor_noise in floor_noise_items if floor_noise.recorded_at <= recorded_at]
        if not candidates:
            return None, None
        floor_noise = candidates[-1]
        return floor_noise.id, floor_noise.artifact_path

    def _artifact_path(self, value) -> Path | None:
        if not isinstance(value, str):
            return None
        path = Path(value)
        if path.is_absolute():
            return path
        return paths.project_root() / path

    def _floor_noise_path(self, transaction_dir: Path, floor_noise_id: str) -> Path | None:
        floor_noise_dir = transaction_dir / "floor_noise"
        if not floor_noise_dir.exists():
            return None
        candidates = sorted(floor_noise_dir.rglob(f"{floor_noise_id}.wav"))
        return candidates[-1] if candidates else None

    def _batch_id(self, entry: AudioCleanupPlanEntry, *, floor_noise_id: str | None = None) -> str:
        profile = entry.profile or entry.resolution
        floor_noise_suffix = f"-{floor_noise_id}" if floor_noise_id else ""
        return f"{entry.role}-{profile}{floor_noise_suffix}".replace("/", "_").replace(" ", "_")


@dataclass(frozen=True)
class AudioCleanupSegmentGroup:
    floor_noise_id: str | None
    floor_noise_path: Path | None
    segment_paths: tuple[Path, ...]


@dataclass(frozen=True)
class ImportedFloorNoise:
    id: str
    recorded_at: str
    artifact_path: Path | None
