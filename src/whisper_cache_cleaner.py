#!/usr/bin/env python3
"""Clear cached whisper transcription entries."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path

import paths


@dataclass
class WhisperCacheCleaner:
    paths: paths.PathConfig
    _logger: logging.Logger = field(init=False, repr=False)
    _cache_dir: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._cache_dir = self.paths.build_dir / "whisper_cache"

    def clear(self, role: str | None = None) -> int:
        if not self._cache_dir.exists():
            return 0
        removed = 0
        for path in self._cache_dir.glob("*.json"):
            if role is not None:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not self._matches_role(payload, role):
                    continue
            path.unlink()
            removed += 1
        return removed

    def _matches_role(self, payload: dict, role: str) -> bool:
        audio_path = payload["audio_path"]
        return Path(audio_path).stem == role
