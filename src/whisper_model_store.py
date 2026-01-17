#!/usr/bin/env python3
"""Load and cache Whisper models in a local directory."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import ClassVar

from faster_whisper import WhisperModel

import paths


@dataclass
class WhisperModelStore:
    paths: paths.PathConfig = field(default_factory=paths.current)
    device: str = "cpu"
    compute_type: str = "int8"
    local_files_only: bool = True
    _logger: logging.Logger = field(init=False, repr=False)

    _model_cache: ClassVar[dict[tuple[str, str, str, bool, Path], WhisperModel]] = {}

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    @property
    def cache_dir(self) -> Path:
        return self.paths.root.parent / ".whisper"

    def load(self, model_name: str) -> WhisperModel:
        cache_dir = self.cache_dir
        key = (model_name, self.device, self.compute_type, self.local_files_only, cache_dir)
        if key not in self._model_cache:
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info(
                "Loading whisper model %s from %s (local_only=%s)",
                model_name,
                cache_dir,
                self.local_files_only,
            )
            self._model_cache[key] = WhisperModel(
                model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(cache_dir),
                local_files_only=self.local_files_only,
            )
        return self._model_cache[key]
