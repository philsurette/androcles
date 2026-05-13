#!/usr/bin/env python3
"""Emit per-role markdown scripts."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from stager.shared import paths
from stager.domain.play import Play, Role, ReadingMetadata
from stager.domain.block import BlockingBlock, RoleBlock


@dataclass
class RoleMarkdownWriter:
    role: Role
    reading_metadata: ReadingMetadata
    play: Play | None = None
    paths: paths.PathConfig = field(default_factory=paths.current)
    prefix_line_nos: bool = field(default=True)
    include_blocking: bool = field(default=False)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (self.paths.markdown_roles_dir / f"{self.role.name}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for blk in self._blocks_for_role():
            if isinstance(blk, RoleBlock):
                prefix = None
                if self.prefix_line_nos:
                    part = blk.block_id.part_id if blk.block_id.part_id is not None else ""
                    prefix = f"{part}.{blk.block_id.block_no} "
                lines.append(blk.to_markdown_for_role(self.role.name, prefix=prefix, include_blocking=self.include_blocking))
            else:
                lines.append(blk.to_markdown(render_id=self.prefix_line_nos))

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target

    def _blocks_for_role(self) -> list:
        if self.play is None:
            return list(self.role.blocks_with_reader())

        blocks = []
        if self.role.reader_block is not None:
            blocks.append(self.role.reader_block)
        for block in self.play.blocks:
            if isinstance(block, RoleBlock):
                if self.role.name in block.role_names:
                    blocks.append(block)
                continue
            if isinstance(block, BlockingBlock) and self.include_blocking and self._blocking_applies_to_role(block):
                blocks.append(block)
        return blocks

    def _blocking_applies_to_role(self, block: BlockingBlock) -> bool:
        return "*" in block.targets or self.role.name in block.targets
