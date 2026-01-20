#!/usr/bin/env python3
"""Cache whisper transcription output to avoid reprocessing unchanged audio."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import re

import paths


@dataclass
class WhisperTranscriptionCache:
    paths: paths.PathConfig
    cache_version: str = "1"
    _logger: logging.Logger = field(init=False, repr=False)
    _cache_dir: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._cache_dir = self.paths.build_dir / "whisper_cache"

    def load(self, cache_key: dict, audio_path: Path) -> list[dict] | None:
        entry_path = None
        for candidate in self._cache_paths(cache_key):
            if candidate.exists():
                entry_path = candidate
                break
        if entry_path is None:
            return None
        payload = json.loads(entry_path.read_text(encoding="utf-8"))
        if payload.get("cache_version") != self.cache_version:
            return None
        stat = audio_path.stat()
        if payload.get("audio_mtime_ns") != stat.st_mtime_ns:
            return None
        if payload.get("audio_size") != stat.st_size:
            return None
        words = payload.get("raw_words")
        if words is None:
            words = payload.get("words")
        if words is None:
            raise RuntimeError(f"Missing cached transcription in {entry_path}")
        self._logger.debug("Using cached transcription for %s", audio_path)
        return words

    def save(self, cache_key: dict, audio_path: Path, raw_words: list[dict]) -> None:
        stat = audio_path.stat()
        payload = {
            "cache_version": self.cache_version,
            "audio_path": str(audio_path),
            "audio_mtime_ns": stat.st_mtime_ns,
            "audio_size": stat.st_size,
            "key": cache_key,
            "raw_words": raw_words,
        }
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        entry_path = self._cache_paths(cache_key)[0]
        entry_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self._logger.debug("Saved transcription cache %s", entry_path)

    def _cache_paths(self, cache_key: dict) -> list[Path]:
        encoded = json.dumps(cache_key, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        role_prefix = self._role_prefix(cache_key)
        if role_prefix:
            return [
                self._cache_dir / f"{role_prefix}-{digest}.json",
                self._cache_dir / f"{digest}.json",
            ]
        return [self._cache_dir / f"{digest}.json"]

    def _role_prefix(self, cache_key: dict) -> str | None:
        audio_path = cache_key.get("audio_path")
        if not audio_path:
            return None
        role = Path(audio_path).stem
        if not role:
            return None
        return re.sub(r"[^A-Za-z0-9_-]+", "_", role)
