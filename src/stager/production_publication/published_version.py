from __future__ import annotations

from dataclasses import dataclass

from stager.production_publication.published_line import PublishedLine
from stager.production_publication.production_version import ProductionVersion


@dataclass(frozen=True)
class PublishedVersion:
    production_version: ProductionVersion
    published_at: str
    source_path: str
    lines: tuple[PublishedLine, ...]
    parent_production_version: ProductionVersion | None = None
    change_summary: str = ""

    @property
    def version(self) -> int:
        return self.production_version.sequence

    @property
    def publication_id(self) -> str:
        return self.production_version.publication_id

    @property
    def label(self) -> str:
        return str(self.production_version)

    @property
    def directory_name(self) -> str:
        return self.production_version.history_directory_name

    def to_dict(self) -> dict:
        data = {
            "production_version": str(self.production_version),
            "sequence": self.production_version.sequence,
            "publication_id": self.production_version.publication_id,
            "label": self.label,
            "published_at": self.published_at,
            "source_path": self.source_path,
            "change_summary": self.change_summary,
            "lines": [line.to_dict() for line in self.lines],
        }
        if self.parent_production_version is not None:
            data["parent_production_version"] = str(self.parent_production_version)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "PublishedVersion":
        production_version = ProductionVersion.parse(data["production_version"])
        parent = data.get("parent_production_version")
        return cls(
            production_version=production_version,
            published_at=data["published_at"],
            source_path=data["source_path"],
            lines=tuple(PublishedLine.from_dict(line) for line in data.get("lines", [])),
            parent_production_version=ProductionVersion.parse(parent) if parent else None,
            change_summary=data.get("change_summary", ""),
        )
