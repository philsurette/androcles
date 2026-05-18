from __future__ import annotations

import pytest

from stager.audio.audio_cleanup_config import CleanupProfile
from stager.audio.audio_cleanup_filter_graph import AudioCleanupFilterGraphCompiler


def test_cleanup_filter_graph_compiles_conservative_filters() -> None:
    profile = CleanupProfile(
        name="voice_cleanup_gentle",
        declick="gentle",
        deesser="gentle",
        denoise="light",
        gate="gentle",
    )

    compiled = AudioCleanupFilterGraphCompiler(
        available_filters={"adeclick", "deesser", "afftdn", "agate"}
    ).compile(profile)

    assert compiled.duration_preserving is True
    assert compiled.filters == (
        "adeclick",
        "deesser=i=0.25",
        "afftdn=nr=6:nf=-50",
        "agate=threshold=0.02:ratio=1.5:attack=20:release=250",
    )
    assert compiled.missing_optional_filters == ()
    assert compiled.duration_preserving is True
    assert compiled.filter_safety == {
        "adeclick": True,
        "deesser": True,
        "afftdn": True,
        "agate": True,
    }


def test_cleanup_filter_graph_disables_missing_optional_filters() -> None:
    profile = CleanupProfile(name="declick", declick="medium", denoise="light")

    compiled = AudioCleanupFilterGraphCompiler(available_filters={"afftdn"}).compile(profile)

    assert compiled.filters == ("afftdn=nr=6:nf=-50",)
    assert compiled.missing_optional_filters == ("adeclick",)


def test_cleanup_filter_graph_rejects_unknown_levels() -> None:
    profile = CleanupProfile(name="bad", declick="extreme")

    with pytest.raises(RuntimeError, match="Unsupported declick level"):
        AudioCleanupFilterGraphCompiler(available_filters={"adeclick"}).compile(profile)
