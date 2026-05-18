from __future__ import annotations

from pathlib import Path

import pytest

from stager.audio.audio_cleanup_config import AudioCleanupConfig, AudioCleanupConfigParser
from stager.shared import paths


def test_missing_cleanup_config_uses_profile_based_defaults(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)

    config = AudioCleanupConfig.load(cfg)
    resolution = config.resolve_role("MEGAERA")

    assert config.cleanup_approach == "profile-based"
    assert config.default_profile == "gentle_voice_cleanup"
    assert config.batch_padding_seconds == 3.0
    assert config.boundary_warning_ms == 500
    assert resolution.kind == "profile"
    assert resolution.profile is not None
    assert resolution.profile.name == "gentle_voice_cleanup"


def test_cleanup_config_resolves_profile_and_analysis_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "audio_cleanup.yaml"
    config_path.write_text(
        """
version: 1
cleanup_approach: analysis-based
default_profile: gentle_voice_cleanup
batch_padding_seconds: 4
boundary_warning_ms: 650
profiles:
  mouth_click_repair:
    declick: medium
    deesser: gentle
    denoise: none
    loudnorm: librivox
roles:
  GOD:
    profile: none
  MEGAERA:
    profile: mouth_click_repair
  ANDROCLES:
    analysis: false
""",
        encoding="utf-8",
    )

    config = AudioCleanupConfigParser().parse(config_path)

    assert config.batch_padding_seconds == 4
    assert config.boundary_warning_ms == 650
    assert config.resolve_role("NARRATOR").kind == "analysis"
    assert config.resolve_role("GOD").kind == "none"
    assert config.resolve_role("MEGAERA").profile.name == "mouth_click_repair"
    assert config.resolve_role("ANDROCLES").profile.name == "gentle_voice_cleanup"


def test_cleanup_config_rejects_conflicting_role_override(tmp_path: Path) -> None:
    config_path = tmp_path / "audio_cleanup.yaml"
    config_path.write_text(
        """
version: 1
roles:
  MEGAERA:
    profile: gentle_voice_cleanup
    analysis: true
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="cannot specify both profile and analysis"):
        AudioCleanupConfigParser().parse(config_path)


def test_cleanup_config_rejects_unknown_profile(tmp_path: Path) -> None:
    config_path = tmp_path / "audio_cleanup.yaml"
    config_path.write_text(
        """
version: 1
default_profile: missing
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Unknown default_profile"):
        AudioCleanupConfigParser().parse(config_path)


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
