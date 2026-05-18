from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from stager.audio.voice_profile_resolver import ResolvedVoiceProfile
from stager.shared import paths


@dataclass(frozen=True)
class VoiceRenderSource:
    layer: str
    path: Path
    content_hash: str
    cleanup_review_id: str | None = None
    cleanup_review_path: Path | None = None
    cleanup_review_hash: str | None = None

    def to_dict(self) -> dict:
        data = {
            "layer": self.layer,
            "path": paths.display_path(self.path),
            "content_hash": self.content_hash,
        }
        if self.cleanup_review_id is not None:
            data["cleanup_review_id"] = self.cleanup_review_id
        if self.cleanup_review_path is not None:
            data["cleanup_review_path"] = paths.display_path(self.cleanup_review_path)
        if self.cleanup_review_hash is not None:
            data["cleanup_review_hash"] = self.cleanup_review_hash
        return data


@dataclass(frozen=True)
class VoiceRenderSegment:
    role: str
    segment_id: str
    source: VoiceRenderSource
    output_path: Path
    cache_key: str
    production_id: str | None = None
    production_content_hash: str | None = None

    def to_dict(self) -> dict:
        data = {
            "role": self.role,
            "segment_id": self.segment_id,
            "source": self.source.to_dict(),
            "output_path": paths.display_path(self.output_path),
            "cache_key": self.cache_key,
        }
        if self.production_id is not None:
            data["production_id"] = self.production_id
        if self.production_content_hash is not None:
            data["production_content_hash"] = self.production_content_hash
        return data


@dataclass(frozen=True)
class VoiceRenderManifest:
    render_profile_id: str
    resolved_profile_id: str
    actor: str
    role: str
    selected_pitch_strategy: str | None
    renderer_backend: str
    renderer_capabilities: dict[str, bool]
    output_format: str
    segments: tuple[VoiceRenderSegment, ...]

    def to_dict(self) -> dict:
        return {
            "render_profile_id": self.render_profile_id,
            "resolved_profile_id": self.resolved_profile_id,
            "actor": self.actor,
            "role": self.role,
            "selected_pitch_strategy": self.selected_pitch_strategy,
            "renderer_backend": self.renderer_backend,
            "renderer_capabilities": self.renderer_capabilities,
            "output_format": self.output_format,
            "segments": [segment.to_dict() for segment in self.segments],
        }


@dataclass
class VoiceRenderCache:
    paths_config: paths.PathConfig

    def render_profile_id(self, resolved_profile: ResolvedVoiceProfile) -> str:
        return f"{resolved_profile.profile_id}-{resolved_profile.stable_id}"

    def output_path(self, *, render_profile_id: str, role: str, segment_id: str, output_format: str = "wav") -> Path:
        return self.paths_config.audio_out_dir / "rendered" / render_profile_id / role / f"{segment_id}.{output_format}"

    def manifest_path(self, render_profile_id: str) -> Path:
        return self.paths_config.audio_out_dir / "rendered" / render_profile_id / "manifest.json"

    def source_identity(
        self,
        *,
        layer: str,
        path: Path,
        cleanup_review_id: str | None = None,
        cleanup_review_path: Path | None = None,
    ) -> VoiceRenderSource:
        return VoiceRenderSource(
            layer=layer,
            path=path,
            content_hash=self.file_hash(path),
            cleanup_review_id=cleanup_review_id,
            cleanup_review_path=cleanup_review_path,
            cleanup_review_hash=self.file_hash(cleanup_review_path) if cleanup_review_path is not None else None,
        )

    def segment_cache_key(
        self,
        *,
        resolved_profile: ResolvedVoiceProfile,
        source: VoiceRenderSource,
        role: str,
        segment_id: str,
        renderer_backend: str,
        renderer_capabilities: dict[str, bool],
        output_format: str = "wav",
        production_id: str | None = None,
        production_content_hash: str | None = None,
    ) -> str:
        payload = {
            "actor": resolved_profile.actor,
            "role": role,
            "segment_id": segment_id,
            "production_id": production_id,
            "production_content_hash": production_content_hash,
            "resolved_profile_id": resolved_profile.stable_id,
            "profile_id": resolved_profile.profile_id,
            "transforms": [asdict(transform) for transform in resolved_profile.transforms],
            "selected_pitch_strategy": resolved_profile.selected_pitch_strategy,
            "observed_metrics": (
                asdict(resolved_profile.observed_metrics) if resolved_profile.observed_metrics is not None else None
            ),
            "source": self._source_payload(source),
            "renderer_backend": renderer_backend,
            "renderer_capabilities": renderer_capabilities,
            "output_format": output_format,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def segment(
        self,
        *,
        resolved_profile: ResolvedVoiceProfile,
        source: VoiceRenderSource,
        segment_id: str,
        renderer_backend: str,
        renderer_capabilities: dict[str, bool],
        output_format: str = "wav",
        production_id: str | None = None,
        production_content_hash: str | None = None,
    ) -> VoiceRenderSegment:
        render_profile_id = self.render_profile_id(resolved_profile)
        cache_key = self.segment_cache_key(
            resolved_profile=resolved_profile,
            source=source,
            role=resolved_profile.role,
            segment_id=segment_id,
            renderer_backend=renderer_backend,
            renderer_capabilities=renderer_capabilities,
            output_format=output_format,
            production_id=production_id,
            production_content_hash=production_content_hash,
        )
        return VoiceRenderSegment(
            role=resolved_profile.role,
            segment_id=segment_id,
            source=source,
            output_path=self.output_path(
                render_profile_id=render_profile_id,
                role=resolved_profile.role,
                segment_id=segment_id,
                output_format=output_format,
            ),
            cache_key=cache_key,
            production_id=production_id,
            production_content_hash=production_content_hash,
        )

    def is_hit(self, segment: VoiceRenderSegment) -> bool:
        if not segment.output_path.exists():
            return False
        manifest_path = self.manifest_path(segment.output_path.parents[1].name)
        if not manifest_path.exists():
            return False
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        for existing in data.get("segments", []):
            if (
                existing.get("role") == segment.role
                and existing.get("segment_id") == segment.segment_id
                and existing.get("cache_key") == segment.cache_key
            ):
                return True
        return False

    def write_manifest(
        self,
        *,
        resolved_profile: ResolvedVoiceProfile,
        renderer_backend: str,
        renderer_capabilities: dict[str, bool],
        segments: tuple[VoiceRenderSegment, ...],
        output_format: str = "wav",
    ) -> Path:
        render_profile_id = self.render_profile_id(resolved_profile)
        manifest = VoiceRenderManifest(
            render_profile_id=render_profile_id,
            resolved_profile_id=resolved_profile.stable_id,
            actor=resolved_profile.actor,
            role=resolved_profile.role,
            selected_pitch_strategy=resolved_profile.selected_pitch_strategy,
            renderer_backend=renderer_backend,
            renderer_capabilities=renderer_capabilities,
            output_format=output_format,
            segments=segments,
        )
        path = self.manifest_path(render_profile_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    def file_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _source_payload(self, source: VoiceRenderSource) -> dict:
        return {
            "layer": source.layer,
            "path": paths.display_path(source.path),
            "content_hash": source.content_hash,
            "cleanup_review_id": source.cleanup_review_id,
            "cleanup_review_path": (
                paths.display_path(source.cleanup_review_path) if source.cleanup_review_path is not None else None
            ),
            "cleanup_review_hash": source.cleanup_review_hash,
        }
