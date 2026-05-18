from __future__ import annotations

from dataclasses import dataclass

from stager.audio.audio_cleanup_batch import CleanupBatchSegment


@dataclass(frozen=True)
class DetectedCleanupBoundary:
    segment_id: str
    cleaned_start_sample: int
    cleaned_end_sample: int
    warnings: tuple[str, ...]


@dataclass
class AudioCleanupBoundaryDetector:
    silence_threshold: float = 0.01

    def detect(
        self,
        *,
        samples: list[float],
        segment: CleanupBatchSegment,
        boundary_warning_samples: int,
    ) -> DetectedCleanupBoundary:
        window_start = max(0, segment.batch_start_sample - segment.guard_before_samples)
        window_end = min(len(samples), segment.batch_end_sample + segment.guard_after_samples)
        active_indices = [
            index
            for index in range(window_start, window_end)
            if abs(samples[index]) > self.silence_threshold
        ]
        if not active_indices:
            return DetectedCleanupBoundary(
                segment_id=segment.segment_id,
                cleaned_start_sample=segment.batch_start_sample,
                cleaned_end_sample=segment.batch_end_sample,
                warnings=("empty_detected_range",),
            )
        cleaned_start = active_indices[0]
        cleaned_end = active_indices[-1] + 1
        warnings = self._warnings(
            segment=segment,
            cleaned_start=cleaned_start,
            cleaned_end=cleaned_end,
            boundary_warning_samples=boundary_warning_samples,
        )
        return DetectedCleanupBoundary(
            segment_id=segment.segment_id,
            cleaned_start_sample=cleaned_start,
            cleaned_end_sample=cleaned_end,
            warnings=tuple(warnings),
        )

    def _warnings(
        self,
        *,
        segment: CleanupBatchSegment,
        cleaned_start: int,
        cleaned_end: int,
        boundary_warning_samples: int,
    ) -> list[str]:
        warnings = []
        if abs(cleaned_start - segment.batch_start_sample) > boundary_warning_samples:
            warnings.append("start_shift")
        if abs(cleaned_end - segment.batch_end_sample) > boundary_warning_samples:
            warnings.append("end_shift")
        original_duration = segment.batch_end_sample - segment.batch_start_sample
        cleaned_duration = cleaned_end - cleaned_start
        if original_duration > 0 and abs(cleaned_duration - original_duration) / original_duration > 0.2:
            warnings.append("duration_shift")
        if not (cleaned_start <= segment.center_sample < cleaned_end):
            warnings.append("center_anchor_missing")
        if segment.guard_before_samples and cleaned_start < segment.batch_start_sample - segment.guard_before_samples // 2:
            warnings.append("approaches_previous_segment")
        if segment.guard_after_samples and cleaned_end > segment.batch_end_sample + segment.guard_after_samples // 2:
            warnings.append("approaches_next_segment")
        return warnings
