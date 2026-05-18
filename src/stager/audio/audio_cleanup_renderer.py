from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Protocol
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


class CommandRunner(Protocol):
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        ...


@dataclass(frozen=True)
class RenderedCleanupBatch:
    manifest: CleanupBatchManifest
    manifest_path: Path
    rendered_count: int
    warning_count: int


@dataclass
class AudioCleanupRenderer:
    paths_config: paths.PathConfig
    sample_rate_hz: int = 48_000
    command_runner: CommandRunner = subprocess.run

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

    def render_batch(
        self,
        *,
        batch_id: str,
        segment_paths: list[Path],
        padding_seconds: float,
        boundary_warning_ms: int,
        resolved_filters: tuple[str, ...],
    ) -> RenderedCleanupBatch:
        prepared = self.prepare_batch(
            batch_id=batch_id,
            segment_paths=segment_paths,
            padding_seconds=padding_seconds,
            boundary_warning_ms=boundary_warning_ms,
            resolved_filters=resolved_filters,
        )
        batch_dir = prepared.manifest_path.parent
        input_path = batch_dir / "batch_input.wav"
        cleaned_path = batch_dir / "batch_cleaned.wav"
        self._write_wav(input_path, self._concatenated_samples(prepared.manifest))
        self._render_with_ffmpeg(
            input_path=input_path,
            output_path=cleaned_path,
            resolved_filters=resolved_filters,
        )
        cleaned_samples = self._read_samples(cleaned_path)
        if abs(len(cleaned_samples) - prepared.manifest.total_samples) > 1:
            raise RuntimeError(
                f"Rendered cleanup batch duration changed unexpectedly for {batch_id}: "
                f"expected {prepared.manifest.total_samples} samples, got {len(cleaned_samples)}"
            )
        boundary_warning_samples = round(boundary_warning_ms / 1000 * prepared.manifest.sample_rate_hz)
        detector = AudioCleanupBoundaryDetector()
        boundaries = []
        rendered_count = 0
        for segment in prepared.manifest.segments:
            detection = detector.detect(
                samples=cleaned_samples,
                segment=segment,
                boundary_warning_samples=boundary_warning_samples,
            )
            output_path = batch_dir / segment.role / f"{segment.segment_id}.wav"
            self._write_wav(output_path, cleaned_samples[detection.cleaned_start_sample : detection.cleaned_end_sample])
            rendered_count += 1
            boundaries.append(
                CleanupBatchBoundaryEntry.from_detection(segment=segment, detection=detection).with_output_path(output_path)
            )
        manifest = prepared.manifest.with_cleaned_boundaries(tuple(boundaries))
        manifest = manifest.with_cache_key(prepared.manifest.cache_key or "")
        cache = AudioCleanupBatchCache(self.paths_config)
        manifest_path = cache.write_manifest(manifest)
        warning_count = sum(1 for boundary in boundaries if boundary.warnings)
        return RenderedCleanupBatch(
            manifest=manifest,
            manifest_path=manifest_path,
            rendered_count=rendered_count,
            warning_count=warning_count,
        )

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

    def _write_wav(self, path: Path, samples: list[float]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate_hz)
            frames = []
            for sample in samples:
                clipped = max(-1.0, min(1.0, sample))
                frames.append(round(clipped * 32767).to_bytes(2, "little", signed=True))
            wav.writeframes(b"".join(frames))

    def _render_with_ffmpeg(
        self,
        *,
        input_path: Path,
        output_path: Path,
        resolved_filters: tuple[str, ...],
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not resolved_filters:
            shutil.copy2(input_path, output_path)
            return
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-af",
            ",".join(resolved_filters),
            str(output_path),
        ]
        result = self.command_runner(command, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or "").strip()
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"Failed to render audio cleanup batch with ffmpeg{suffix}")
