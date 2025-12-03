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
        return f"{self.block_id}_{self.segment_no}"
