from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from play_config import PlayConfig, DEFAULT_PLAY_ID, DEFAULT_BUILD_TYPE


def test_play_config_default_when_missing(tmp_path) -> None:
    cfg = PlayConfig.load(tmp_path)

    assert cfg.play_id == DEFAULT_PLAY_ID
    assert cfg.build_type == DEFAULT_BUILD_TYPE


def test_play_config_loads_values(tmp_path) -> None:
    config_path = tmp_path / "play-config.yaml"
    config_path.write_text("play_id: test\nbuild_type: custom\n", encoding="utf-8")

    cfg = PlayConfig.load(tmp_path)

    assert cfg.play_id == "test"
    assert cfg.build_type == "custom"


def test_play_config_rejects_invalid_types(tmp_path) -> None:
    config_path = tmp_path / "play-config.yaml"
    config_path.write_text("play_id:\n  - bad\nbuild_type: custom\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        PlayConfig.load(tmp_path)
