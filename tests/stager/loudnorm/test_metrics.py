from __future__ import annotations

from stager.loudnorm.metric import LoudnessProfile, Metrics


def test_default_metrics_use_librivox_targets() -> None:
    metrics = Metrics()

    assert metrics.for_name("lufs").target_range.target == -21
    assert metrics.for_name("peak").target_range.target == -1
    assert metrics.for_name("range").target_range.target == 10


def test_metrics_can_use_podcast_profile() -> None:
    metrics = Metrics.for_profile(LoudnessProfile.podcast())

    assert metrics.for_name("lufs").target_range.target == -14
    assert metrics.for_name("lufs").as_filter_option() == "i=-14"
