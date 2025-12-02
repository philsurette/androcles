#!/usr/bin/env python3
"""Identifiers for play segments."""
from __future__ import annotations

from dataclasses import dataclass

from block_id import BlockId


@dataclass
class SegmentId:
    block_id: BlockId
    segment_no: int

    def __str__(self) -> str:
        part_str = "" if getattr(self.block_id, "part_id", None) is None else str(self.block_id.part_id)
        return f"{part_str}_{self.block_id.block_no}_{self.segment_no}"
