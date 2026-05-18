from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import wave

from stager.audio.audio_cleanup_batch import (
    AudioCleanupBatchBuilder,
    AudioCleanupBatchCache,
    CleanupBatchBoundaryEntry,
    CleanupBatchManifest,
)
from stager.audio.audio_cleanup_boundaries import AudioCleanupBoundaryDetector
from stager.shared import paths


@dataclass(frozen=True)
class PreparedCleanupBatch:
    manifest: CleanupBatchManifest
    manifest_path: Path
    cache_hit: bool


@dataclass
class AudioCleanupRenderer:
    paths_config: paths.PathConfig
    sample_rate_hz: int = 48_000

    def prepare_batch(
        self,
        *,
        batch_id: str,
        segment_paths: list[Path],
        padding_seconds: float,
        boundary_warning_ms: int,
        resolved_filters: tuple[str, ...],
    ) -> PreparedCleanupBatch:
        builder = AudioCleanupBatchBuilder(sample_rate_hz=self.sample_rate_hz)
        manifest = builder.build(
            batch_id=batch_id,
            segment_paths=segment_paths,
            padding_seconds=padding_seconds,
        )
        samples = self._concatenated_samples(manifest)
        boundary_warning_samples = round(boundary_warning_ms / 1000 * manifest.sample_rate_hz)
        detector = AudioCleanupBoundaryDetector()
        boundaries = tuple(
            CleanupBatchBoundaryEntry.from_detection(
                segment=segment,
                detection=detector.detect(
                    samples=samples,
                    segment=segment,
                    boundary_warning_samples=boundary_warning_samples,
                ),
            )
            for segment in manifest.segments
        )
        manifest = manifest.with_cleaned_boundaries(boundaries)
        cache = AudioCleanupBatchCache(self.paths_config)
        cache_key = cache.cache_key(
            manifest=manifest,
            resolved_filters=resolved_filters,
            boundary_warning_ms=boundary_warning_ms,
        )
        manifest = manifest.with_cache_key(cache_key)
        cache_hit = cache.is_hit(manifest)
        manifest_path = cache.write_manifest(manifest)
        return PreparedCleanupBatch(manifest=manifest, manifest_path=manifest_path, cache_hit=cache_hit)

    def _concatenated_samples(self, manifest: CleanupBatchManifest) -> list[float]:
        samples: list[float] = []
        for segment in manifest.segments:
            if segment.guard_before_samples and len(samples) < segment.batch_start_sample:
                samples.extend([0.0] * (segment.batch_start_sample - len(samples)))
            samples.extend(self._read_samples(segment.source_path))
            if segment.guard_after_samples:
                samples.extend([0.0] * segment.guard_after_samples)
        if len(samples) < manifest.total_samples:
            samples.extend([0.0] * (manifest.total_samples - len(samples)))
        return samples

    def _read_samples(self, path: Path) -> list[float]:
        with wave.open(str(path), "rb") as wav:
            sample_width = wav.getsampwidth()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
        samples = []
        for offset in range(0, len(frames), sample_width):
            sample_bytes = frames[offset : offset + sample_width]
            if len(sample_bytes) != sample_width:
                break
            if sample_width == 1:
                sample = (sample_bytes[0] - 128) / 128
            elif sample_width == 2:
                sample = int.from_bytes(sample_bytes, "little", signed=True) / 32768
            elif sample_width == 3:
                sample = int.from_bytes(
                    sample_bytes + (b"\xff" if sample_bytes[-1] & 0x80 else b"\x00"),
                    "little",
                    signed=True,
                ) / 8388608
            elif sample_width == 4:
                sample = int.from_bytes(sample_bytes, "little", signed=True) / 2147483648
            else:
                raise RuntimeError(f"Unsupported WAV sample width {sample_width} in {paths.display_path(path)}")
            samples.append(sample)
        return samples
