#!/usr/bin/env python3
"""Emit per-role markdown scripts."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import paths
from play import Role, ReadingMetadata
from block import RoleBlock


@dataclass
class RoleMarkdownWriter:
    role: Role
    reading_metadata: ReadingMetadata
    paths: paths.PathConfig = field(default_factory=paths.current)
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (self.paths.markdown_roles_dir / f"{self.role.name}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for blk in self.role.blocks_with_reader():
            if isinstance(blk, RoleBlock):
                prefix = None
                if self.prefix_line_nos:
                    part = blk.block_id.part_id if blk.block_id.part_id is not None else ""
                    prefix = f"{part}.{blk.block_id.block_no} "
                lines.append(blk.to_markdown_for_role(self.role.name, prefix=prefix))
            else:
                lines.append(blk.to_markdown(render_id=self.prefix_line_nos))

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
