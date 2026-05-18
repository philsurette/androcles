from __future__ import annotations

from pathlib import Path

from stager.audio.audio_cleanup_batch import CleanupBatchSegment
from stager.audio.audio_cleanup_boundaries import AudioCleanupBoundaryDetector


def test_boundary_detector_trims_to_active_audio_and_warns_on_large_shift() -> None:
    segment = _segment(start=10, end=110, center=60)
    samples = [0.0] * 130
    for index in range(20, 72):
        samples[index] = 0.2

    detected = AudioCleanupBoundaryDetector().detect(
        samples=samples,
        segment=segment,
        boundary_warning_samples=20,
    )

    assert detected.cleaned_start_sample == 20
    assert detected.cleaned_end_sample == 72
    assert detected.warnings == ("end_shift", "duration_shift")


def test_boundary_detector_warns_when_center_anchor_is_missing() -> None:
    segment = _segment(start=10, end=110, center=60)
    samples = [0.0] * 130
    for index in range(20, 40):
        samples[index] = 0.2

    detected = AudioCleanupBoundaryDetector().detect(
        samples=samples,
        segment=segment,
        boundary_warning_samples=20,
    )

    assert "center_anchor_missing" in detected.warnings


def test_boundary_detector_warns_when_detection_approaches_neighbor_padding() -> None:
    segment = _segment(start=100, end=200, center=150, guard_before=80, guard_after=80)
    samples = [0.0] * 300
    for index in range(150, 245):
        samples[index] = 0.2

    detected = AudioCleanupBoundaryDetector().detect(
        samples=samples,
        segment=segment,
        boundary_warning_samples=20,
    )

    assert "approaches_next_segment" in detected.warnings


def test_boundary_detector_marks_empty_detection() -> None:
    segment = _segment(start=10, end=110, center=60)

    detected = AudioCleanupBoundaryDetector().detect(
        samples=[0.0] * 130,
        segment=segment,
        boundary_warning_samples=20,
    )

    assert detected.cleaned_start_sample == 10
    assert detected.cleaned_end_sample == 110
    assert detected.warnings == ("empty_detected_range",)


def _segment(
    *,
    start: int,
    end: int,
    center: int,
    guard_before: int = 0,
    guard_after: int = 0,
) -> CleanupBatchSegment:
    return CleanupBatchSegment(
        role="MEGAERA",
        segment_id="0_1_1",
        source_path=Path("0_1_1.wav"),
        source_hash="hash",
        source_sample_rate_hz=48_000,
        source_frames=end - start,
        batch_start_sample=start,
        batch_end_sample=end,
        center_sample=center,
        guard_before_samples=guard_before,
        guard_after_samples=guard_after,
    )
