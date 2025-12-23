#!/usr/bin/env python3
"""Emit narrator/meta markdown script."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import paths
from play import Play, ReadingMetadata
from block import TitleBlock, DescriptionBlock, DirectionBlock, RoleBlock, DirectionSegment, SpeechSegment


@dataclass
class NarratorMarkdownWriter:
    play: Play
    reading_metadata: ReadingMetadata
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write narrator/meta text into build/markdown/roles/_NARRATOR.md."""
        target = out_path or (paths.MARKDOWN_ROLES_DIR / "_NARRATOR.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []

        narrator_name = self.reading_metadata.reader_for_id("_NARRATOR").reader
        lines.append(f"Narrated by {narrator_name}\n")

        for blk in self.play.blocks:
            part_id = blk.block_id.part_id if blk.block_id.part_id is not None else ""
            block_line = f"{part_id}.{blk.block_id.block_no}"
            if isinstance(blk, (DescriptionBlock)):
                lines.append(block_line)
                lines.append(f"{blk.to_markdown(render_id='')}")
                lines.append("")
                continue
            if isinstance(blk, (DirectionBlock)):
                lines.append(block_line)
                lines.append(f"  - {blk.to_markdown(render_id='')}")
                lines.append("")
                continue
            if isinstance(blk, (TitleBlock)):
                lines.append(block_line)
                lines.append(f"# {blk.to_markdown(render_id='')}")
                lines.append("")
                continue
            if isinstance(blk, RoleBlock):
                if not any(isinstance(seg, (DirectionSegment, SpeechSegment)) and getattr(seg, "role", "_NARRATOR") == "_NARRATOR" for seg in blk.segments):
                    continue
                lines.append(block_line)
                for seg in blk.segments:
                    segment_prefix = "  - "
                    if isinstance(seg, DirectionSegment) or (isinstance(seg, SpeechSegment) and getattr(seg, "role", "_NARRATOR") == "_NARRATOR"):
                        lines.append(f"{segment_prefix}{seg.text}")
                lines.append("")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
