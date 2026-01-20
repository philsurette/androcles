#!/usr/bin/env python3
"""Load play configuration defaults from play-config.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

DEFAULT_PLAY_ID = "androcles"
DEFAULT_BUILD_TYPE = "librivox"


@dataclass
class PlayConfig:
    play_id: str
    build_type: str

    @classmethod
    def default(cls) -> "PlayConfig":
        return cls(play_id=DEFAULT_PLAY_ID, build_type=DEFAULT_BUILD_TYPE)

    @classmethod
    def load(cls, root: Path | None = None) -> "PlayConfig":
        base_dir = root or Path(__file__).resolve().parent.parent
        config_path = base_dir / "play-config.yaml"
        if not config_path.exists():
            return cls.default()
        yml = YAML(typ="safe", pure=True)
        data = yml.load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise RuntimeError(f"Invalid play-config.yaml format: {config_path}")
        play_id = data.get("play_id", DEFAULT_PLAY_ID)
        build_type = data.get("build_type", DEFAULT_BUILD_TYPE)
        if not isinstance(play_id, str):
            raise RuntimeError(f"Invalid play_id in {config_path}: {play_id!r}")
        if not isinstance(build_type, str):
            raise RuntimeError(f"Invalid build_type in {config_path}: {build_type!r}")
        return cls(play_id=play_id, build_type=build_type)
