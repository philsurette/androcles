#!/usr/bin/env python3
"""Resolve the effective build target for commands."""
from __future__ import annotations

from dataclasses import dataclass, field

from stager.shared import paths
from stager.shared.play_config import PlayConfig


@dataclass
class BuildTypeResolver:
    paths_config: paths.PathConfig = field(default_factory=paths.current)
    explicit_build_type: str | None = None
    librivox_override: bool | None = None

    def resolve(self) -> str:
        if self.explicit_build_type is not None:
            return self._normalize(self.explicit_build_type)
        if self.librivox_override is not None:
            return "librivox" if self.librivox_override else "custom"
        return self._normalize(PlayConfig.load(self.paths_config.root.parent).build_type)

    def _normalize(self, build_type: str) -> str:
        normalized = build_type.strip().lower()
        if normalized not in {"custom", "librivox"}:
            raise RuntimeError(f"Unknown build type: {build_type}")
        return normalized
