from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

from stager.playbook.cue_start_offset_analyzer import CueStartOffsetAnalyzer
from stager.playbook.cue_window_presets import CueWindowPresets


def _write_tone_with_silence(
    path: Path,
    *,
    duration_ms: int,
    silence_start_ms: int | None = None,
    silence_end_ms: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_rate = 8_000
    frame_count = int(frame_rate * duration_ms / 1000)
    silence_start = int(frame_rate * (silence_start_ms or 0) / 1000)
    silence_end = int(frame_rate * (silence_end_ms or 0) / 1000)
    frames = bytearray()
    for frame_index in range(frame_count):
        if silence_start_ms is not None and silence_start <= frame_index < silence_end:
            sample = 0
        else:
            sample = int(12000 * math.sin(2 * math.pi * 440 * frame_index / frame_rate))
        frames.extend(struct.pack("<h", sample))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(frame_rate)
        wav.writeframes(bytes(frames))


def test_analyzer_default_windows_match_shared_presets() -> None:
    assert CueStartOffsetAnalyzer().windows_ms == CueWindowPresets().timed_windows_ms()


def test_preset_file_contains_initial_timed_windows() -> None:
    preset_path = Path("planning/specs/cue_window_presets.json")
    data = json.loads(preset_path.read_text(encoding="utf-8"))
    timed_windows = [
        preset["window_ms"]
        for preset in data["cue_window_presets"]
        if preset["window_ms"] is not None
    ]

    assert timed_windows == [5000, 10000, 15000, 20000]


def test_short_audio_offsets_start_at_zero(tmp_path: Path) -> None:
    audio_path = tmp_path / "short.wav"
    _write_tone_with_silence(audio_path, duration_ms=2000)
    analyzer = CueStartOffsetAnalyzer(windows_ms=[5000, 10000])

    offsets = analyzer.analyze(audio_path, duration_ms=2000)

    assert [
        (offset.requested_window_ms, offset.start_ms, offset.confidence)
        for offset in offsets
    ] == [
        (5000, 0, "exact"),
        (10000, 0, "exact"),
    ]


def test_analyzer_uses_quiet_boundary_near_requested_window(tmp_path: Path) -> None:
    audio_path = tmp_path / "cue.wav"
    _write_tone_with_silence(
        audio_path,
        duration_ms=16000,
        silence_start_ms=5900,
        silence_end_ms=6100,
    )
    analyzer = CueStartOffsetAnalyzer(windows_ms=[10000])

    offsets = analyzer.analyze(audio_path, duration_ms=16000)

    assert len(offsets) == 1
    assert offsets[0].requested_window_ms == 10000
    assert offsets[0].confidence == "boundary"
    assert 5900 <= offsets[0].start_ms <= 6100


def test_analyzer_falls_back_when_no_quiet_boundary_exists(tmp_path: Path) -> None:
    audio_path = tmp_path / "cue.wav"
    _write_tone_with_silence(audio_path, duration_ms=16000)
    analyzer = CueStartOffsetAnalyzer(windows_ms=[10000])

    offsets = analyzer.analyze(audio_path, duration_ms=16000)

    assert [(offset.start_ms, offset.confidence) for offset in offsets] == [(6000, "fallback")]


def test_analyzer_omits_offsets_for_compressed_audio() -> None:
    analyzer = CueStartOffsetAnalyzer(windows_ms=[10000])

    assert analyzer.analyze(Path("cue.mp3"), duration_ms=16000) == []
