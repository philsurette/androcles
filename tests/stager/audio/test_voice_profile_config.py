from __future__ import annotations

from pathlib import Path

import pytest

from stager.audio.voice_profile_config import VoiceProfileConfig, VoiceProfileConfigParser
from stager.shared import paths


def test_missing_voice_profile_config_is_empty(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)

    config = VoiceProfileConfig.load(cfg)

    assert config.actors == {}
    assert config.role_targets == {}
    assert config.cast_profiles == {}


def test_voice_profile_config_parses_cast_profiles_and_observed_metrics(tmp_path: Path) -> None:
    config_path = tmp_path / "voice_profiles.yaml"
    config_path.write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
    baseline:
      pitch_center_hz: 115
      speaking_rate_wpm: 155
      brightness: neutral
role_targets:
  MEGAERA:
    description: Brighter voice.
    target:
      pitch_center_hz: 205
      speaking_rate_wpm: 165
      max_pitch_shift_semitones: 6
      tempo_policy:
        mode: preserve_performance
        acceptable_range_wpm: [145, 190]
        max_linked_speed_change: 0.08
        min_confidence: 0.75
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true
        fallback: preserve_tempo
observed_metrics:
  phil@MEGAERA:
    speaking_rate_wpm: 178
    confidence: 0.82
    source: manual
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
    overrides:
      pitch_shift_semitones: 5.5
""",
        encoding="utf-8",
    )

    config = VoiceProfileConfigParser().parse(config_path)

    assert config.actors["phil"].pitch_center_hz == 115
    assert config.role_targets["MEGAERA"].tempo_policy.acceptable_range_wpm == (145, 190)
    assert config.observed_metrics["phil@MEGAERA"].speaking_rate_wpm == 178
    assert config.cast_profiles["phil@MEGAERA"].overrides["pitch_shift_semitones"] == 5.5


def test_voice_profile_config_rejects_legacy_pitch_preserve_tempo_flag(tmp_path: Path) -> None:
    config_path = tmp_path / "voice_profiles.yaml"
    config_path.write_text(
        """
version: 1
actors:
  alex:
    baseline:
      pitch_center_hz: 180
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
cast_profiles:
  alex@MEGAERA:
    actor: alex
    role: MEGAERA
    mode: explicit
    transforms:
      - type: pitch
        semitones: 1.5
        preserve_tempo: true
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must use strategy"):
        VoiceProfileConfigParser().parse(config_path)


def test_voice_profile_config_rejects_duplicate_actor_role_bindings(tmp_path: Path) -> None:
    config_path = tmp_path / "voice_profiles.yaml"
    config_path.write_text(
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
cast_profiles:
  first:
    actor: phil
    role: MEGAERA
    mode: computed
  second:
    actor: phil
    role: MEGAERA
    mode: computed
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Duplicate cast profile binding"):
        VoiceProfileConfigParser().parse(config_path)


def test_voice_profile_config_rejects_computed_profile_without_pitch_baseline(tmp_path: Path) -> None:
    config_path = tmp_path / "voice_profiles.yaml"
    config_path.write_text(
        """
version: 1
actors:
  phil:
    baseline:
      speaking_rate_wpm: 155
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="requires actor and role pitch_center_hz"):
        VoiceProfileConfigParser().parse(config_path)


def _cfg(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True)
    return cfg
