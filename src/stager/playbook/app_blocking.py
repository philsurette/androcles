from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stager.domain.segment import BlockingSegment


@dataclass
class AppBlocking:
    id: str
    targets: list[str]
    text: str
    placement: str
    segment_id: str | None = None
    content_hash: str | None = None

    @classmethod
    def from_segment(cls, segment: BlockingSegment, placement: str) -> "AppBlocking":
        if segment.production_id is None:
            raise RuntimeError(f"Missing production id for blocking segment {segment.segment_id}")
        return cls(
            id=segment.production_id,
            targets=list(segment.targets),
            text=segment.text,
            placement=placement,
            segment_id=str(segment.segment_id),
            content_hash=segment.content_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "targets": list(self.targets),
            "text": self.text,
            "placement": self.placement,
            **({"segment_id": self.segment_id} if self.segment_id is not None else {}),
            **({"content_hash": self.content_hash} if self.content_hash is not None else {}),
        }
