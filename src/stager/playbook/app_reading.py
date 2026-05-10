from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stager.domain.play import Play


@dataclass
class AppReading:
    type: str
    build_type: str

    @classmethod
    def from_play(cls, play: Play, build_type: str) -> "AppReading":
        return cls(
            type=play.reading_metadata.reading_type,
            build_type=build_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "build_type": self.build_type,
        }
