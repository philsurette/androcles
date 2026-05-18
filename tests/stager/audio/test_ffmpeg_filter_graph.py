from __future__ import annotations

import pytest

from stager.audio.ffmpeg_filter_graph import FfmpegFilterGraphCompiler
from stager.audio.voice_profile_config import VoiceTransform


def test_filter_graph_compiles_basic_voice_shaping_filters() -> None:
    graph = FfmpegFilterGraphCompiler().compile(
        (
            VoiceTransform(type="highpass", params={"frequency_hz": 120}),
            VoiceTransform(type="lowpass", params={"frequency_hz": 9000}),
            VoiceTransform(type="eq", params={"frequency_hz": 3000, "gain_db": 3, "width": 1.2}),
            VoiceTransform(
                type="compressor",
                params={"threshold_db": -18, "ratio": 2.5, "attack_ms": 5, "release_ms": 80},
            ),
            VoiceTransform(type="gain", params={"db": -1.5}),
        )
    )

    assert graph.filters == (
        "highpass=f=120.0",
        "lowpass=f=9000.0",
        "equalizer=f=3000.0:width_type=o:width=1.2:g=3.0",
        "acompressor=threshold=-18.0dB:ratio=2.5:attack=5.0:release=80.0",
        "volume=-1.5dB",
    )


def test_filter_graph_compiles_preserve_tempo_pitch() -> None:
    graph = FfmpegFilterGraphCompiler(sample_rate_hz=48000).compile(
        (
            VoiceTransform(
                type="pitch",
                params={"semitones": 12, "strategy": "preserve_tempo"},
            ),
        )
    )

    assert graph.filters == (
        "asetrate=48000*2",
        "aresample=48000",
        "atempo=0.5",
    )


def test_filter_graph_compiles_linked_speed_pitch_without_tempo_restore() -> None:
    graph = FfmpegFilterGraphCompiler(sample_rate_hz=48000).compile(
        (
            VoiceTransform(
                type="pitch",
                params={"semitones": 12, "strategy": "linked_speed"},
            ),
        )
    )

    assert graph.filters == (
        "asetrate=48000*2",
        "aresample=48000",
    )


def test_filter_graph_rejects_unresolved_auto_pitch() -> None:
    with pytest.raises(RuntimeError, match="must be resolved"):
        FfmpegFilterGraphCompiler().compile(
            (
                VoiceTransform(
                    type="pitch",
                    params={"semitones": 1, "strategy": "auto"},
                ),
            )
        )


def test_filter_graph_expands_filter_curve_to_equalizers() -> None:
    graph = FfmpegFilterGraphCompiler().compile(
        (
            VoiceTransform(
                type="filter_curve",
                params={"points": [[120, -6], [3000, 3]]},
            ),
        )
    )

    assert graph.filters == (
        "equalizer=f=120.0:width_type=o:width=1:g=-6.0",
        "equalizer=f=3000.0:width_type=o:width=1:g=3.0",
    )


def test_filter_graph_compiles_speed_reverb_delay_and_loudnorm() -> None:
    graph = FfmpegFilterGraphCompiler().compile(
        (
            VoiceTransform(type="speed", params={"speed_factor": 1.25}),
            VoiceTransform(type="reverb", params={"delay_ms": 80, "decay": 0.4}),
            VoiceTransform(type="delay", params={"delay_ms": 120, "decay": 0.25}),
            VoiceTransform(type="loudnorm", params={"integrated_lufs": -18, "true_peak_db": -2, "lra": 10}),
        )
    )

    assert graph.filters == (
        "atempo=1.25",
        "aecho=0.8:0.9:80.0:0.4",
        "aecho=0.8:0.9:120.0:0.25",
        "loudnorm=I=-18.0:TP=-2.0:LRA=10.0",
    )


def test_filter_graph_rejects_unexpanded_presets() -> None:
    with pytest.raises(RuntimeError, match="Preset transforms must be expanded"):
        FfmpegFilterGraphCompiler().compile(
            (
                VoiceTransform(type="preset", params={"name": "female_bright"}),
            )
        )
