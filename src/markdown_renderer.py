#!/usr/bin/env python3
"""Utilities to emit PlayText into markdown-friendly blocks."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import OrderedDict
from pathlib import Path

import paths
from play import Play, Role, Reader, ReadingMetadata
from block import Block, TitleBlock, DescriptionBlock, DirectionBlock, RoleBlock, DirectionSegment, SpeechSegment


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


@dataclass
class CalloutsMarkdownWriter:
    play: Play

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write callouts.md listing callouts and their associated roles."""
        target = out_path or (paths.MARKDOWN_DIR / "_CALLOUTS.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        callouts: OrderedDict[str, list[str]] = OrderedDict()

        for blk in self.play.blocks:
            if not isinstance(blk, RoleBlock):
                continue
            callout = blk.callout
            if callout is None:
                continue
            roles = blk.role_names if getattr(blk, "role_names", None) else [blk.primary_role]
            if callout not in callouts:
                callouts[callout] = []
            for role in roles:
                if role not in callouts[callout]:
                    callouts[callout].append(role)

        lines: list[str] = []
        for callout in sorted(callouts.keys()):
            roles = callouts[callout]
            lines.append(f"# {callout}")
            for role in roles:
                lines.append(f"* {role}")
            lines.append("")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target


@dataclass
class CalloutScriptWriter:
    play: Play

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """
        Write _CALLER.md listing each callout to record in a single _CALLOUT.wav.
        Callouts are sorted alphabetically and use the callout name as the id.
        """
        target = out_path or (paths.MARKDOWN_ROLES_DIR / "_CALLER.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        callouts: list[str] = []
        seen: set[str] = set()
        for blk in self.play.blocks:
            if not isinstance(blk, RoleBlock):
                continue
            if blk.callout is None:
                continue
            if blk.callout in seen:
                continue
            seen.add(blk.callout)
            callouts.append(blk.callout)

        lines: list[str] = []
        for name in sorted(callouts):
            lines.append(f"- {name}")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target
    
@dataclass
class RoleMarkdownWriter:
    role: Role
    reading_metadata: ReadingMetadata
    prefix_line_nos: bool = field(default=True)

    def to_markdown(self, out_path: Path | None = None) -> Path:
        """Write blocks.md with one block per paragraph, separated by a blank line."""
        target = out_path or (paths.MARKDOWN_ROLES_DIR / f"{self.role.name}.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        rm = getattr(self.reading_metadata, "dramatic_reading", False)
        if rm:
            reader: Reader = self.reading_metadata.reader_for_id(self.role.name)
            role_label = reader.role_name
            reader_name = reader.reader if reader.reader else self.reading_metadata.default_reader.reader
            lines.append(f"{role_label}, read by {reader_name}")

        for blk in self.role.blocks:
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
                # part = blk.block_id.part_id if blk.block_id.part_id is not None else ""
                # block_prefix = f"{part}.{blk.block_id.block_no} " if self.prefix_line_nos else ""
                # lines.append(block_prefix)
                lines.append(block_line)
                for seg in blk.segments:
                    #segment_prefix = f"  - .{seg.segment_id.segment_no} " if self.prefix_line_nos else ""
                    segment_prefix = "  - "
                    if isinstance(seg, DirectionSegment) or (isinstance(seg, SpeechSegment) and getattr(seg, "role", "_NARRATOR") == "_NARRATOR"):
                        lines.append(f"{segment_prefix}{seg.text}")
                lines.append("")

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return target

    
