from __future__ import annotations

from pathlib import Path

import pytest

from stager.production.cast_config import CastConfig, CastConfigParser
from stager.shared import paths


def test_missing_cast_config_is_empty(tmp_path: Path) -> None:
    config = CastConfigParser().parse(tmp_path / "cast.yaml")

    assert config.actors == {}
    assert config.roles == {}


def test_cast_config_parses_actor_role_assignments(tmp_path: Path) -> None:
    path = tmp_path / "cast.yaml"
    path.write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
    email: phil@example.com
roles:
  MEGAERA:
    actor: phil
    recording: whole-role
    voice_profile: phil@MEGAERA
""",
        encoding="utf-8",
    )

    config = CastConfigParser().parse(path)

    assert config.actors["phil"].display_name == "Phil"
    assert config.actors["phil"].email == "phil@example.com"
    assert config.roles["MEGAERA"].actor == "phil"
    assert config.roles["MEGAERA"].recording == "whole-role"
    assert config.roles["MEGAERA"].voice_profile == "phil@MEGAERA"


def test_cast_config_rejects_unknown_actor(tmp_path: Path) -> None:
    path = tmp_path / "cast.yaml"
    path.write_text(
        """
version: 1
roles:
  MEGAERA:
    actor: phil
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="unknown actor"):
        CastConfigParser().parse(path)


def test_cast_config_rejects_invalid_recording_method(tmp_path: Path) -> None:
    path = tmp_path / "cast.yaml"
    path.write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  MEGAERA:
    actor: phil
    recording: studio
""",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Invalid recording method"):
        CastConfigParser().parse(path)


def test_cast_config_loads_from_play_dir(tmp_path: Path) -> None:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil
roles:
  MEGAERA:
    actor: phil
""",
        encoding="utf-8",
    )

    assert CastConfig.load(cfg).roles["MEGAERA"].actor == "phil"
