#!/usr/bin/env python3
"""Identifiers for blocks within a play."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlockId:
    part_id: int | None
    block_no: int

    def nextId(self) -> "BlockId":
        """Return the next BlockId within the same part."""
        return BlockId(self.part_id, self.block_no + 1)

    def previousId(self) -> "BlockId | None":
        """Return the previous BlockId within the same part, or None if this is the first."""
        if self.block_no <= 0:
            return None
        return BlockId(self.part_id, self.block_no - 1)

    def __hash__(self) -> int:  # Ensure hashability for dict/set usage.
        return hash((self.part_id, self.block_no))
