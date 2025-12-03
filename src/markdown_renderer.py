#!/usr/bin/env python3
"""Utilities to emit PlayText into markdown-friendly blocks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import paths
from play_text import PlayText, Role
from block import Block, MetaBlock, DescriptionBlock, DirectionBlock, RoleBlock, DirectionSegment, SpeechSegment


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


@dataclass
class NarratorMarkdownWriter:
    play: PlayText
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write narrator/meta text into build/markdown/roles/_NARRATOR.md."""
        target = out_path or (paths.MARKDOWN_ROLES_DIR / "_NARRATOR.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        for blk in self.play:
            if isinstance(blk, (MetaBlock, DescriptionBlock, DirectionBlock)):
                lines.append(blk.to_markdown(render_id=self.prefix_line_nos))
                lines.append("")
                continue
            if isinstance(blk, RoleBlock):
                if not any(isinstance(seg, (DirectionSegment, SpeechSegment)) and getattr(seg, "role", "_NARRATOR") == "_NARRATOR" for seg in blk.segments):
                    continue
                part = blk.block_id.part_id if blk.block_id.part_id is not None else ""
                block_prefix = f"{part}.{blk.block_id.block_no} " if self.prefix_line_nos else ""
                lines.append(block_prefix)
                for seg in blk.segments:
                    segment_prefix = f"  * .{seg.segment_id.segment_no} " if self.prefix_line_nos else ""
                    if isinstance(seg, DirectionSegment) or (isinstance(seg, SpeechSegment) and getattr(seg, "role", "_NARRATOR") == "_NARRATOR"):
                        lines.append(f"{segment_prefix}{seg.text}")
                lines.append("")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target

    
