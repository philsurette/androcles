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

    @classmethod
    def from_dict(cls, data: dict) -> "ProductionChange":
        return cls(
            kind=data["kind"],
            line_id=data["line_id"],
            current=PublishedLine.from_dict(data["current"]) if data.get("current") else None,
            previous=PublishedLine.from_dict(data["previous"]) if data.get("previous") else None,
            recommended_id=data.get("recommended_id"),
        )
