from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppProduction:
    source: str
    version: str | None = None
    sequence: int | None = None
    publication_id: str | None = None
    parent_version: str | None = None
    published_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"source": self.source}
        if self.version is not None:
            data["version"] = self.version
        if self.sequence is not None:
            data["sequence"] = self.sequence
        if self.publication_id is not None:
            data["publication_id"] = self.publication_id
        if self.parent_version is not None:
            data["parent_version"] = self.parent_version
        if self.published_at is not None:
            data["published_at"] = self.published_at
        return data

