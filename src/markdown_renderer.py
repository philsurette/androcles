#!/usr/bin/env python3
"""Utilities to emit PlayText into markdown-friendly blocks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import paths
from play_text import PlayText, Role
from block import *


@dataclass
class PlayMarkdownWriter:
    play: PlayText
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (paths.MARKDOWN_DIR / f"{self.play.title}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [blk.to_markdown(render_id=self.prefix_line_nos) for blk in self.play.blocks]

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
    
@dataclass
class RoleMarkdownWriter:
    role: Role
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (paths.MARKDOWN_ROLES_DIR / f"{self.role.name}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [blk.to_markdown(render_id=self.prefix_line_nos) for blk in self.role.blocks]

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target

    
