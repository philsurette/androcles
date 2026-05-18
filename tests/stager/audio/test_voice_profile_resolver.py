from __future__ import annotations

from pathlib import Path

import pytest

from stager.audio.voice_profile_config import VoiceProfileConfigParser
from stager.audio.voice_profile_resolver import VoiceProfileResolver


def test_voice_profile_resolver_allows_one_actor_reading_multiple_roles(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  ANDROCLES:
    target:
      pitch_center_hz: 130
  MEGAERA:
    target:
      pitch_center_hz: 205
      max_pitch_shift_semitones: 6
cast_profiles:
  phil@ANDROCLES:
    actor: phil
    role: ANDROCLES
    mode: computed
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
""",
    )

    resolver = VoiceProfileResolver(config)

    androcles = resolver.resolve("ANDROCLES")
    megaera = resolver.resolve("MEGAERA")

    assert androcles is not None
    assert megaera is not None
    assert androcles.actor == "phil"
    assert megaera.actor == "phil"
    assert androcles.transforms[0].params["semitones"] != megaera.transforms[0].params["semitones"]


def test_voice_profile_resolver_allows_two_actors_reading_same_role_with_explicit_actor(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
  alex:
    baseline:
      pitch_center_hz: 180
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
  alex@MEGAERA:
    actor: alex
    role: MEGAERA
    mode: explicit
    transforms:
      - type: pitch
        semitones: 1.5
        strategy: preserve_tempo
""",
    )

    resolved = VoiceProfileResolver(config).resolve("MEGAERA", actor="alex")

    assert resolved is not None
    assert resolved.actor == "alex"
    assert resolved.mode == "explicit"
    assert resolved.selected_pitch_strategy == "preserve_tempo"
    assert resolved.transforms[0].params["semitones"] == 1.5


def test_voice_profile_resolver_fails_when_actor_selection_is_ambiguous(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
  alex:
    baseline:
      pitch_center_hz: 180
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 205
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
  alex@MEGAERA:
    actor: alex
    role: MEGAERA
    mode: computed
""",
    )

    with pytest.raises(RuntimeError, match="Ambiguous actor"):
        VoiceProfileResolver(config).resolve("MEGAERA")


def test_voice_profile_resolver_clamps_computed_pitch_and_applies_overrides(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 100
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 300
      max_pitch_shift_semitones: 4
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
    overrides:
      pitch_shift_semitones: 3.5
""",
    )

    resolved = VoiceProfileResolver(config).resolve("MEGAERA")

    assert resolved is not None
    assert resolved.transforms[0].params["semitones"] == 3.5


def test_voice_profile_resolver_selects_linked_speed_when_tempo_policy_allows_it(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
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
        acceptable_range_wpm: [145, 190]
        max_linked_speed_change: 0.08
        min_confidence: 0.75
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true
observed_metrics:
  phil@MEGAERA:
    speaking_rate_wpm: 178
    confidence: 0.9
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
""",
    )

    resolved = VoiceProfileResolver(config).resolve("MEGAERA")

    assert resolved is not None
    assert resolved.selected_pitch_strategy == "linked_speed"
    assert resolved.transforms[0].params["strategy"] == "linked_speed"


def test_voice_profile_resolver_preserves_tempo_when_predicted_wpm_is_outside_policy(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  MEGAERA:
    target:
      pitch_center_hz: 129.1
      tempo_policy:
        acceptable_range_wpm: [145, 190]
        max_linked_speed_change: 0.20
        min_confidence: 0.75
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true
observed_metrics:
  phil@MEGAERA:
    speaking_rate_wpm: 178
    confidence: 0.9
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
""",
    )

    resolved = VoiceProfileResolver(config).resolve("MEGAERA")

    assert resolved is not None
    assert resolved.selected_pitch_strategy == "preserve_tempo"
    assert "outside policy" in resolved.warnings[0]


def test_voice_profile_resolver_preserves_tempo_when_observed_tempo_is_missing(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
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
        acceptable_range_wpm: [145, 190]
        max_linked_speed_change: 0.08
      pitch_strategy:
        prefer_linked_speed_pitch_when_safe: true
cast_profiles:
  phil@MEGAERA:
    actor: phil
    role: MEGAERA
    mode: computed
""",
    )

    resolved = VoiceProfileResolver(config).resolve("MEGAERA")

    assert resolved is not None
    assert resolved.selected_pitch_strategy == "preserve_tempo"
    assert "no observed tempo" in resolved.warnings[0]


def test_voice_profile_resolver_expands_presets(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
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
presets:
  female_bright_subtle:
    transforms:
      - type: highpass
        frequency_hz: 120
cast_profiles:
  alex@MEGAERA:
    actor: alex
    role: MEGAERA
    mode: explicit
    transforms:
      - type: preset
        name: female_bright_subtle
      - type: pitch
        semitones: 1.5
        strategy: preserve_tempo
""",
    )

    resolved = VoiceProfileResolver(config).resolve("MEGAERA")

    assert resolved is not None
    assert [transform.type for transform in resolved.transforms] == ["highpass", "pitch"]


def test_voice_profile_resolver_expands_builtin_presets_deterministically(tmp_path: Path) -> None:
    config = _parse(
        tmp_path,
        """
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
  GOD:
    target:
      pitch_center_hz: 95
      preset: godlike_hall
cast_profiles:
  phil@GOD:
    actor: phil
    role: GOD
    mode: computed
""",
    )

    resolved = VoiceProfileResolver(config).resolve("GOD")

    assert resolved is not None
    assert [transform.type for transform in resolved.transforms] == [
        "filter_curve",
        "reverb",
        "compressor",
        "pitch",
    ]
    assert resolved.transforms[1].params == {"delay_ms": 90, "decay": 0.45}


def _parse(tmp_path: Path, content: str):
    path = tmp_path / "voice_profiles.yaml"
    path.write_text(content, encoding="utf-8")
    return VoiceProfileConfigParser().parse(path)
