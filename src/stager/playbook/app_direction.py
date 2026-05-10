from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stager.domain.segment import DescriptionSegment, DirectionSegment


@dataclass
class AppDirection:
    segment_id: str
    text: str
    placement: str

    @classmethod
    def from_segment(cls, segment: DescriptionSegment | DirectionSegment, placement: str) -> "AppDirection":
        return cls(
            segment_id=str(segment.segment_id),
            text=segment.text,
            placement=placement,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "text": self.text,
            "placement": self.placement,
        }
