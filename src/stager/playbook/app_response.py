from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stager.playbook.app_response_segment import AppResponseSegment


@dataclass
class AppResponse:
    text: str
    segments: list[AppResponseSegment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "segments": [segment.to_dict() for segment in self.segments],
        }
