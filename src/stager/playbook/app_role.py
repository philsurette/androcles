from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stager.domain.play import Play, Role
from stager.playbook.app_line import AppLine


@dataclass
class AppRole:
    id: str
    display_name: str
    reader: str
    meta: bool = False
    parts: list[int | None] = field(default_factory=list)
    lines: list[AppLine] = field(default_factory=list)

    @classmethod
    def from_domain(cls, play: Play, role: Role) -> "AppRole":
        reader = play.reading_metadata.reader_for_id(role.name)
        return cls(
            id=role.name,
            display_name=reader.role_name or role.name,
            reader=reader.reader or play.reading_metadata.default_reader.reader or "Anonymous",
            meta=role.meta,
            parts=sorted({block.block_id.part_id for block in role.blocks}, key=lambda part_id: -1 if part_id is None else part_id),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "reader": self.reader,
            "meta": self.meta,
            "parts": list(self.parts),
            "lines": [line.to_dict() for line in self.lines],
        }
