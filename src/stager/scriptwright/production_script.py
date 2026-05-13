"""Production markdown model objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProductionEntryKind(str, Enum):
    HEADING = "heading"
    DESCRIPTION = "description"
    DIRECTION = "direction"
    BLOCKING = "blocking"
    ROLE = "role"


@dataclass(frozen=True)
class ProductionEntry:
    kind: ProductionEntryKind
    text: str
    line_no: int
    production_id: str | None = None
    heading_level: int | None = None
    roles: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    leading_comments: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProductionScript:
    metadata: dict[str, str]
    entries: tuple[ProductionEntry, ...] = field(default_factory=tuple)

    @property
    def locked(self) -> bool:
        return self.metadata["production_ids"] == "locked"
