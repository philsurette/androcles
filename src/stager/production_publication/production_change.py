from __future__ import annotations

from dataclasses import dataclass

from stager.production_publication.published_line import PublishedLine


@dataclass(frozen=True)
class ProductionChange:
    kind: str
    line_id: str
    current: PublishedLine | None = None
    previous: PublishedLine | None = None
    recommended_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "line_id": self.line_id,
            **({"recommended_id": self.recommended_id} if self.recommended_id else {}),
            **({"current": self.current.to_dict()} if self.current else {}),
            **({"previous": self.previous.to_dict()} if self.previous else {}),
        }
