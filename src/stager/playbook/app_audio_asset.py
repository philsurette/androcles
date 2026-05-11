from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from stager.playbook.app_cue_start_offset import AppCueStartOffset


@dataclass
class AppAudioAsset:
    path: PurePosixPath
    duration_ms: int
    required: bool = True
    cue_start_offsets: list[AppCueStartOffset] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "path": self.path.as_posix(),
            "duration_ms": self.duration_ms,
            "required": self.required,
        }
        if self.cue_start_offsets:
            data["cue_start_offsets"] = [
                offset.to_dict()
                for offset in self.cue_start_offsets
            ]
        return data
