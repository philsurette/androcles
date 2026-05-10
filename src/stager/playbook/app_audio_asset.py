from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


@dataclass
class AppAudioAsset:
    path: PurePosixPath
    duration_ms: int
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path.as_posix(),
            "duration_ms": self.duration_ms,
            "required": self.required,
        }
