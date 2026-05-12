from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stager.domain.block import RoleBlock
from stager.playbook.app_cue import AppCue
from stager.playbook.app_direction import AppDirection
from stager.playbook.app_response import AppResponse


@dataclass
class AppLine:
    id: str
    part_id: int | None
    block_id: str
    role: str
    speaker: str
    cue: AppCue
    response: AppResponse
    content_hash: str | None = None
    directions: list[AppDirection] = field(default_factory=list)
    previous_roles: list[str] = field(default_factory=list)
    simultaneous: bool = False

    @classmethod
    def line_id_for(cls, block: RoleBlock, role: str) -> str:
        if block.production_id is not None:
            return block.production_id
        return f"{block.block_id}_{role}"

    @classmethod
    def block_id_for(cls, block: RoleBlock) -> str:
        part = block.block_id.part_id if block.block_id.part_id is not None else ""
        return f"{part}.{block.block_id.block_no}"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "part_id": self.part_id,
            "block_id": self.block_id,
            "role": self.role,
            "speaker": self.speaker,
            "cue": self.cue.to_dict(),
            "response": self.response.to_dict(),
            "directions": [direction.to_dict() for direction in self.directions],
            "previous_roles": list(self.previous_roles),
        }
        if self.content_hash is not None:
            data["content_hash"] = self.content_hash
        if self.simultaneous:
            data["simultaneous"] = True
        return data
