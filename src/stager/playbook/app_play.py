from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stager.domain.play import Play


@dataclass
class AppPlay:
    id: str
    title: str
    authors: list[str] = field(default_factory=list)
    source: str | None = None

    @classmethod
    def from_play(cls, play_id: str, play: Play) -> "AppPlay":
        return cls(
            id=play_id,
            title=play.source_text_metadata.title,
            authors=list(play.source_text_metadata.authors),
            source=play.source_text_metadata.source,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "authors": list(self.authors),
        }
        if self.source is not None:
            data["source"] = self.source
        return data
