from __future__ import annotations

from dataclasses import dataclass
import hashlib
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

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "sample_rate_hz": self.sample_rate_hz,
            "padding_seconds": self.padding_seconds,
            "padding_samples": self.padding_samples,
            "total_samples": self.total_samples,
            "segments": [segment.to_dict() for segment in self.segments],
        }


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
