from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import wave

from stager.shared import paths


@dataclass(frozen=True)
class CleanupBatchSegment:
    role: str
    segment_id: str
    source_path: Path
    source_hash: str
    source_sample_rate_hz: int
    source_frames: int
    batch_start_sample: int
    batch_end_sample: int
    center_sample: int
    guard_before_samples: int
    guard_after_samples: int

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "segment_id": self.segment_id,
            "source_path": paths.display_path(self.source_path),
            "source_hash": self.source_hash,
            "source_sample_rate_hz": self.source_sample_rate_hz,
            "source_frames": self.source_frames,
            "batch_start_sample": self.batch_start_sample,
            "batch_end_sample": self.batch_end_sample,
            "center_sample": self.center_sample,
            "guard_before_samples": self.guard_before_samples,
            "guard_after_samples": self.guard_after_samples,
        }


@dataclass(frozen=True)
class CleanupBatchManifest:
    batch_id: str
    sample_rate_hz: int
    padding_seconds: float
    padding_samples: int
    total_samples: int
    segments: tuple[CleanupBatchSegment, ...]
    cleaned_boundaries: tuple["CleanupBatchBoundaryEntry", ...] = ()
    cache_key: str | None = None

    def to_dict(self) -> dict:
        data = {
            "batch_id": self.batch_id,
            "sample_rate_hz": self.sample_rate_hz,
            "padding_seconds": self.padding_seconds,
            "padding_samples": self.padding_samples,
            "total_samples": self.total_samples,
            "segments": [segment.to_dict() for segment in self.segments],
        }
        if self.cache_key is not None:
            data["cache_key"] = self.cache_key
        if self.cleaned_boundaries:
            data["cleaned_boundaries"] = [boundary.to_dict() for boundary in self.cleaned_boundaries]
        return data

    def with_cleaned_boundaries(
        self,
        cleaned_boundaries: tuple["CleanupBatchBoundaryEntry", ...],
    ) -> "CleanupBatchManifest":
        return CleanupBatchManifest(
            batch_id=self.batch_id,
            sample_rate_hz=self.sample_rate_hz,
            padding_seconds=self.padding_seconds,
            padding_samples=self.padding_samples,
            total_samples=self.total_samples,
            segments=self.segments,
            cleaned_boundaries=cleaned_boundaries,
            cache_key=self.cache_key,
        )

    def with_cache_key(self, cache_key: str) -> "CleanupBatchManifest":
        return CleanupBatchManifest(
            batch_id=self.batch_id,
            sample_rate_hz=self.sample_rate_hz,
            padding_seconds=self.padding_seconds,
            padding_samples=self.padding_samples,
            total_samples=self.total_samples,
            segments=self.segments,
            cleaned_boundaries=self.cleaned_boundaries,
            cache_key=cache_key,
        )


@dataclass(frozen=True)
class CleanupBatchBoundaryEntry:
    role: str
    segment_id: str
    original_start_sample: int
    original_end_sample: int
    original_center_sample: int
    cleaned_start_sample: int
    cleaned_end_sample: int
    warnings: tuple[str, ...]
    output_path: Path | None = None
    validation: dict | None = None

    @classmethod
    def from_detection(
        cls,
        *,
        segment: CleanupBatchSegment,
        detection,
    ) -> "CleanupBatchBoundaryEntry":
        return cls(
            role=segment.role,
            segment_id=segment.segment_id,
            original_start_sample=segment.batch_start_sample,
            original_end_sample=segment.batch_end_sample,
            original_center_sample=segment.center_sample,
            cleaned_start_sample=detection.cleaned_start_sample,
            cleaned_end_sample=detection.cleaned_end_sample,
            output_path=None,
            warnings=detection.warnings,
            validation=None,
        )

    def with_output(self, *, output_path: Path, validation: dict) -> "CleanupBatchBoundaryEntry":
        return CleanupBatchBoundaryEntry(
            role=self.role,
            segment_id=self.segment_id,
            original_start_sample=self.original_start_sample,
            original_end_sample=self.original_end_sample,
            original_center_sample=self.original_center_sample,
            cleaned_start_sample=self.cleaned_start_sample,
            cleaned_end_sample=self.cleaned_end_sample,
            output_path=output_path,
            warnings=self.warnings,
            validation=validation,
        )

    def to_dict(self) -> dict:
        data = {
            "role": self.role,
            "segment_id": self.segment_id,
            "original_start_sample": self.original_start_sample,
            "original_end_sample": self.original_end_sample,
            "original_center_sample": self.original_center_sample,
            "cleaned_start_sample": self.cleaned_start_sample,
            "cleaned_end_sample": self.cleaned_end_sample,
            "warnings": list(self.warnings),
        }
        if self.output_path is not None:
            data["output_path"] = paths.display_path(self.output_path)
        if self.validation is not None:
            data["validation"] = self.validation
        return data


@dataclass
class AudioCleanupBatchBuilder:
    sample_rate_hz: int = 48_000

    def build(
        self,
        *,
        batch_id: str,
        segment_paths: list[Path],
        padding_seconds: float,
    ) -> CleanupBatchManifest:
        if padding_seconds <= 0:
            raise RuntimeError("Audio cleanup batch padding must be positive")
        padding_samples = round(padding_seconds * self.sample_rate_hz)
        cursor = 0
        segments = []
        for index, path in enumerate(segment_paths):
            metadata = self._metadata(path)
            if metadata.sample_rate_hz != self.sample_rate_hz:
                raise RuntimeError(
                    f"Audio cleanup batch expected {self.sample_rate_hz} Hz but found "
                    f"{metadata.sample_rate_hz} Hz in {paths.display_path(path)}"
                )
            guard_before = padding_samples if index > 0 else 0
            start_sample = cursor
            end_sample = start_sample + metadata.frames
            center_sample = start_sample + metadata.frames // 2
            cursor = end_sample
            guard_after = padding_samples if index < len(segment_paths) - 1 else 0
            segments.append(
                CleanupBatchSegment(
                    role=path.parent.name,
                    segment_id=path.stem,
                    source_path=path,
                    source_hash=self._hash(path),
                    source_sample_rate_hz=metadata.sample_rate_hz,
                    source_frames=metadata.frames,
                    batch_start_sample=start_sample,
                    batch_end_sample=end_sample,
                    center_sample=center_sample,
                    guard_before_samples=guard_before,
                    guard_after_samples=guard_after,
                )
            )
            cursor += guard_after
        return CleanupBatchManifest(
            batch_id=batch_id,
            sample_rate_hz=self.sample_rate_hz,
            padding_seconds=padding_seconds,
            padding_samples=padding_samples,
            total_samples=cursor,
            segments=tuple(segments),
        )

    def _metadata(self, path: Path) -> "_AudioMetadata":
        with wave.open(str(path), "rb") as wav:
            return _AudioMetadata(sample_rate_hz=wav.getframerate(), frames=wav.getnframes())

    def _hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


@dataclass(frozen=True)
class _AudioMetadata:
    sample_rate_hz: int
    frames: int


@dataclass
class AudioCleanupBatchCache:
    paths_config: paths.PathConfig

    def cache_key(
        self,
        *,
        manifest: CleanupBatchManifest,
        resolved_filters: tuple[str, ...],
        boundary_warning_ms: int,
    ) -> str:
        payload = {
            "sample_rate_hz": manifest.sample_rate_hz,
            "padding_seconds": manifest.padding_seconds,
            "boundary_warning_ms": boundary_warning_ms,
            "resolved_filters": list(resolved_filters),
            "segments": [
                {
                    "role": segment.role,
                    "segment_id": segment.segment_id,
                    "source_hash": segment.source_hash,
                    "start": segment.batch_start_sample,
                    "end": segment.batch_end_sample,
                    "center": segment.center_sample,
                }
                for segment in manifest.segments
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def manifest_path(self, batch_id: str) -> Path:
        return self.paths_config.audio_out_dir / "cleaned" / batch_id / "batch_manifest.json"

    def is_hit(self, manifest: CleanupBatchManifest) -> bool:
        if manifest.cache_key is None:
            return False
        path = self.manifest_path(manifest.batch_id)
        if not path.exists():
            return False
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        return existing.get("cache_key") == manifest.cache_key

    def write_manifest(self, manifest: CleanupBatchManifest) -> Path:
        path = self.manifest_path(manifest.batch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path
