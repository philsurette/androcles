from __future__ import annotations

from dataclasses import dataclass

from stager.production_publication.published_line import PublishedLine


@dataclass(frozen=True)
class PublishedVersion:
    version: int
    published_at: str
    source_path: str
    lines: tuple[PublishedLine, ...]

    @property
    def label(self) -> str:
        return f"v{self.version:04d}"

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "label": self.label,
            "published_at": self.published_at,
            "source_path": self.source_path,
            "lines": [line.to_dict() for line in self.lines],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PublishedVersion":
        return cls(
            version=data["version"],
            published_at=data["published_at"],
            source_path=data["source_path"],
            lines=tuple(PublishedLine.from_dict(line) for line in data.get("lines", [])),
        )
