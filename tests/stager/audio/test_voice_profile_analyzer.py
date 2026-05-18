from __future__ import annotations

import json
import math
from pathlib import Path
import wave

import pytest

from stager.audio.voice_profile_analyzer import VoiceProfileAnalyzer
from stager.audio.voice_profile_config import VoiceProfileConfigParser
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.domain.block import RoleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.shared import paths


def test_voice_profile_analyzer_writes_observed_metric_suggestions(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    play = _play(role="MEGAERA", texts=["one two three four"])
    _write_sine(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", frequency_hz=100, duration_seconds=1.0)

    report = VoiceProfileAnalyzer(paths_config=cfg, play=play).analyze(actor="phil", role="MEGAERA")

    data = json.loads(report.json_path.read_text(encoding="utf-8"))
    result = report.results[0]
    assert result.actor == "phil"
    assert result.role == "MEGAERA"
    assert result.word_count == 4
    assert result.speaking_rate_wpm is not None
    assert 220 <= result.speaking_rate_wpm <= 260
    assert result.pitch_center_hz is not None
    assert 90 <= result.pitch_center_hz <= 110
    assert result.confidence == 0.35
    assert data["voice_profiles_yaml_suggestions"]["phil@MEGAERA"]["source"] == "analysis"


def test_voice_profile_analyzer_marks_larger_roles_confident(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    texts = [" ".join(f"word{i}x{j}" for j in range(30)) for i in range(5)]
    play = _play(role="MEGAERA", texts=texts)
    for index in range(1, 6):
        _write_sine(cfg.segments_dir / "MEGAERA" / f"0_{index}_1.wav", frequency_hz=120, duration_seconds=1.0)

    report = VoiceProfileAnalyzer(paths_config=cfg, play=play).analyze(actor="phil", role="MEGAERA")

    assert report.results[0].word_count == 150
    assert report.results[0].segment_count == 5
    assert report.results[0].confidence == 0.9


def test_voice_profile_analysis_can_feed_pitch_strategy_without_speed_normalization(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    texts = [" ".join(f"word{i}x{j}" for j in range(30)) for i in range(5)]
    play = _play(role="MEGAERA", texts=texts)
    for index in range(1, 6):
        _write_sine(cfg.segments_dir / "MEGAERA" / f"0_{index}_1.wav", frequency_hz=120, duration_seconds=1.0)
    report = VoiceProfileAnalyzer(paths_config=cfg, play=play).analyze(actor="phil", role="MEGAERA")
    suggestion = json.loads(report.json_path.read_text(encoding="utf-8"))["voice_profiles_yaml_suggestions"]["phil@MEGAERA"]
    config_path = tmp_path / "voice_profiles.yaml"
    config_path.write_text(
        f"""
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 122.1
      tempo_policy:
        acceptable_range_wpm: [1000, 2200]
        max_linked_speed_change: 0.08
        min_confidence: 0.75
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true
observed_metrics:
  phil@MEGAERA:
    speaking_rate_wpm: {suggestion["speaking_rate_wpm"]}
    confidence: {suggestion["confidence"]}
    source: analysis
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
""",
        encoding="utf-8",
    )

    resolved = VoiceProfileResolver(VoiceProfileConfigParser().parse(config_path)).resolve("MEGAERA")

    assert resolved is not None
    assert resolved.selected_pitch_strategy == "linked_speed"
    assert [transform.type for transform in resolved.transforms] == ["pitch"]


def test_voice_profile_analyzer_fails_for_missing_segment_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    play = _play(role="MEGAERA", texts=["one two"])

    with pytest.raises(RuntimeError, match="Audio file missing"):
        VoiceProfileAnalyzer(paths_config=cfg, play=play).analyze(actor="phil", role="MEGAERA")


def _play(*, role: str, texts: list[str]) -> Play:
    blocks = []
    for index, text in enumerate(texts, start=1):
        block_id = BlockId(0, index)
        blocks.append(
            RoleBlock(
                block_id=block_id,
                role_names=[role],
                text=text,
                segments=[
                    SpeechSegment(
                        segment_id=SegmentId(block_id, 1),
                        text=text,
                        role=role,
                    )
                ],
            )
        )
    return Play(
        source_text_metadata=SourceTextMetadata(title="Test"),
        reading_metadata=ReadingMetadata(reading_type="solo"),
        blocks=blocks,
    )


def _write_sine(path: Path, *, frequency_hz: float, duration_seconds: float, sample_rate: int = 8_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sample_rate * duration_seconds)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []
        for frame in range(frame_count):
            value = int(12_000 * math.sin(2 * math.pi * frequency_hz * frame / sample_rate))
            frames.append(value.to_bytes(2, "little", signed=True))
        wav.writeframes(b"".join(frames))


def _cfg(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    return cfg
