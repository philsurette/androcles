#!/usr/bin/env python3
"""Utilities to emit PlayText into markdown-friendly blocks (full play)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import paths
from play import Play


@dataclass
class PlayMarkdownWriter:
    play: Play
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (paths.MARKDOWN_DIR / f"{self.play.title}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [blk.to_markdown(render_id=self.prefix_line_nos) for blk in self.play.blocks]

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
