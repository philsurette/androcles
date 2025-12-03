#!/usr/bin/env python3
"""Utilities to emit PlayText into markdown-friendly blocks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from play_text import PlayText
from block import *
from paths import BUILD_DIR


@dataclass
class PlayTextWriter:
    play_text: PlayText
    prefix_line_nos: bool = field(default=True)

    def write_blocks(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (BUILD_DIR / "text" / "blocks.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [blk.to_markdown(render_id=self.prefix_line_nos) for blk in self.play_text]

        target.write_text("\n\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
    

