#!/usr/bin/env python3
"""Utilities to emit PlayText into markdown-friendly blocks (full play)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from stager.shared import paths
from stager.domain.block import Block, BlockingBlock, RoleBlock
from stager.domain.play import Play


@dataclass
class PlayMarkdownWriter:
    play: Play
    paths: paths.PathConfig = field(default_factory=paths.current)
    prefix_line_nos: bool = field(default=True)
    include_blocking: bool = field(default=False)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (self.paths.markdown_dir / f"{self._filename_for_title(self.play.title)}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            self._block_to_markdown(block, prefix)
            for block, prefix in self._numbered_blocks()
        ]

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target

    def _filename_for_title(self, title: str) -> str:
        filename = re.sub(r"\s+", "_", title.strip())
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
        filename = filename.strip("._")
        return filename or "Untitled"

    def _include_block(self, block) -> bool:
        return self.include_blocking or not isinstance(block, BlockingBlock)

    def _numbered_blocks(self) -> list[tuple[Block, str | None]]:
        counters: dict[int | None, int] = {}
        numbered_blocks: list[tuple[Block, str | None]] = []
        for block in self.play.blocks:
            if not self._include_block(block):
                continue
            part_id = block.block_id.part_id
            if block.block_id.block_no == 0:
                counters[part_id] = 0
                display_no = 0
            else:
                counters[part_id] = counters.get(part_id, 0) + 1
                display_no = counters[part_id]
            if not self.prefix_line_nos:
                numbered_blocks.append((block, None))
                continue
            part = "" if part_id is None else part_id
            numbered_blocks.append((block, f"{part}.{display_no} "))
        return numbered_blocks

    def _block_to_markdown(self, block, prefix: str | None) -> str:
        if isinstance(block, RoleBlock):
            return block.to_markdown_for_role(
                block.primary_role,
                prefix=prefix,
                include_blocking=self.include_blocking,
            )
        return block.to_markdown(prefix=prefix)
