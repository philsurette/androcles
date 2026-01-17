#!/usr/bin/env python3
"""Block representing the reader intro line for a role."""
from __future__ import annotations

from dataclasses import dataclass

from block import Block
from block_id import BlockId


@dataclass
class ReaderBlock(Block):
    role_label: str = ""
    reader_name: str = ""

    @classmethod
    def build(cls, role_label: str, reader_name: str) -> "ReaderBlock":
        block_id = BlockId(part_id=None, block_no=0)
        text = f"{role_label}, read by {reader_name}"
        return cls(block_id=block_id, text=text, role_label=role_label, reader_name=reader_name)

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> "ReaderBlock | None":
        return None

    def _to_markdown(self, prefix: str | None) -> str:
        return self.text
