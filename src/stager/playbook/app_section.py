from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppSection:
    id: str
    part_id: int | None
    block_id: str | None
    title: str
    ordinal: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "block_id": self.block_id,
            "title": self.title,
            "ordinal": self.ordinal,
        }
