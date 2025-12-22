#!/usr/bin/env python3
"""Data structures and parsing for play text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import re
from pathlib import Path
import paths
from block_id import BlockId
from segment import DirectionSegment, SpeechSegment, SimultaneousSegment
from block import Block, MetaBlock, DescriptionBlock, DirectionBlock, RoleBlock

@dataclass
class Title:
    part_no: int
    title: str

@dataclass
class Role:
    """A collection of blocks belonging to a role."""

    name: str
    blocks: List[RoleBlock] = field(default_factory=list)
    meta: bool = False

    def get_blocks(self, part_no: int | None = None) -> List[RoleBlock]:
        """Return role blocks, optionally filtered by part number."""
        if part_no is None:
            return list(self.blocks)
        return [blk for blk in self.blocks if blk.block_id.part_id == part_no]

    def segments(self, part_no: int | None = None) -> dict[tuple[int | None, int], list[str]]:
        """Return mapping (part, block) -> ordered segment ids for this role."""
        mapping: dict[tuple[int | None, int], list[str]] = {}
        for blk in self.get_blocks(part_no):
            key = (blk.block_id.part_id, blk.block_id.block_no)
            for seg in blk.segments:
                if isinstance(seg, SpeechSegment) and seg.role == self.name:
                    seg_id = f"{'' if key[0] is None else key[0]}_{key[1]}_{seg.segment_id.segment_no}"
                    mapping.setdefault(key, []).append(seg_id)
                elif isinstance(seg, SimultaneousSegment) and self.name in getattr(seg, "roles", []):
                    seg_id = f"{'' if key[0] is None else key[0]}_{key[1]}_{seg.segment_id.segment_no}"
                    mapping.setdefault(key, []).append(seg_id)
        return mapping


@dataclass
class NarratorRole(Role):
    """Special role for narrator/meta segments."""

    meta: bool = True

    def segments(self, part_no: int | None = None) -> dict[tuple[int | None, int], list[str]]:
        mapping: dict[tuple[int | None, int], list[str]] = {}
        for blk in self.blocks if part_no is None else [b for b in self.blocks if b.block_id.part_id == part_no]:
            key = (blk.block_id.part_id, blk.block_id.block_no)
            for seg in blk.segments:
                seg_id = f"{'' if key[0] is None else key[0]}_{key[1]}_{seg.segment_id.segment_no}"
                mapping.setdefault(key, []).append(seg_id)
        return mapping


@dataclass
class Part:
    """A collection of blocks belonging to a part."""

    part_no: int | None
    title: str | None
    blocks: List[Block] = field(default_factory=list)


class Play(List[Block]):
    def __init__(self, items: List[Block] | None = None) -> None:
        super().__init__(items or [])
        self._by_id: dict[BlockId, Block] = {}
        for block in self:
            self._by_id[block.block_id] = block
        self._parts: dict[int | None, Part] = {}
        self._part_order: List[int | None] = []
        self._roles: dict[str, Role] = {}
        self._role_order: List[str] = []
        if items:
            self._build_parts_index()

    def getPrecedingRoles(
        self,
        block_id: BlockId,
        num_preceding: int = 2,
        limit_to_current_part: bool = True,
        include_meta_roles: bool = False,
    ) -> List[str]:
        """
        Return the last `num_preceding` distinct roles (by appearance) prior to block_id.
        """
        roles: List[str] = []
        for blk in self:
            if blk.block_id.part_id == block_id.part_id and blk.block_id.block_no == block_id.block_no:
                break
            if limit_to_current_part and blk.block_id.part_id != block_id.part_id:
                continue
            if isinstance(blk, RoleBlock):
                speaker_list: List[str] = []
                has_inline_dirs = any(isinstance(seg, DirectionSegment) for seg in blk.segments)
                if has_inline_dirs:
                    speaker_list.append("_NARRATOR")
                if getattr(blk, "callout", None):
                    speaker_list.append(getattr(blk, "callout"))
                if getattr(blk, "role_names", None):
                    speaker_list.extend(getattr(blk, "role_names"))
                for role in speaker_list:
                    if not include_meta_roles and role.startswith("_"):
                        continue
                    roles.append(role)
        distinct: List[str] = []
        for role in reversed(roles):
            if role not in distinct:
                distinct.append(role)
            if len(distinct) >= num_preceding:
                break
        return list(reversed(distinct))

    def block_for_id(self, block_id: BlockId) -> Block | None:
        """Return the Block for the given id, or None if not present."""
        return self._by_id.get(block_id)

    def _build_parts_index(self) -> None:
        heading_re = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
        self._parts.clear()
        self._part_order.clear()
        self._roles.clear()
        self._role_order.clear()
        for blk in self:
            pid = blk.block_id.part_id
            if pid not in self._parts:
                title: str | None = None
                if isinstance(blk, MetaBlock) and blk.text.startswith("##"):
                    m = heading_re.match(blk.text.strip())
                    if m:
                        title = m.group(2).strip()
                self._parts[pid] = Part(part_no=pid, title=title, blocks=[])
                self._part_order.append(pid)
            self._parts[pid].blocks.append(blk)
            if isinstance(blk, RoleBlock):
                speaker_list = blk.role_names if getattr(blk, "role_names", None) else [blk.primary_role]
                for role_name in speaker_list:
                    if role_name not in self._roles:
                        if role_name == "_NARRATOR":
                            self._roles[role_name] = NarratorRole(name=role_name, blocks=[], meta=True)
                        else:
                            self._roles[role_name] = Role(name=role_name, blocks=[])
                        self._role_order.append(role_name)
                    self._roles[role_name].blocks.append(blk)

    def getPart(self, part_id: int | None) -> Part | None:
        """Return the Part object for the given id."""
        if not self._parts:
            self._build_parts_index()
        return self._parts.get(part_id)
    
    @property
    def first_part_id(self) -> int:
        """Return the first part id in the play."""
        if not self._parts:
            self._build_parts_index()
        return [p.part_no for p in self.parts if p.part_no is not None][0]

    @property
    def last_part_id(self) -> int:
        """Return the last part id in the play."""
        if not self._parts:
            self._build_parts_index()
        return [p.part_no for p in self.parts if p.part_no is not None][-1]

    @property
    def parts(self) -> List[Part]:
        """Return all Part objects in play order."""
        if not self._parts:
            self._build_parts_index()
        return [self._parts[pid] for pid in self._part_order]

    def getParts(self) -> List[Part]:
        """Return all Part objects in play order."""
        if not self._parts:
            self._build_parts_index()
        return [self._parts[pid] for pid in self._part_order]

    def getRole(self, role_name: str) -> Role | None:
        """Return Role object for the given name."""
        if not self._roles:
            self._build_parts_index()
        return self._roles.get(role_name)

    @property
    def blocks(self) -> List[Block]:
        """Return the list of blocks."""
        return list(self)

    @property
    def title(self) -> str:
        """Return the text of the first block."""
        return self[0].text if self else ""

    @property
    def author(self) -> str:
        """Return the text of the first block."""
        return self[1].text if self else ""

    @property
    def roles(self) -> List[Role]:
        """Return all roles in play order of first appearance."""
        if not self._roles:
            self._build_parts_index()
        return [self._roles[name] for name in self._role_order]

    def getRoles(self) -> List[Role]:
        """Return all roles in play order of first appearance."""
        if not self._roles:
            self._build_parts_index()
        return [self._roles[name] for name in self._role_order]

    def rebuild_parts_index(self) -> None:
        """Recompute part mapping from current blocks."""
        self._build_parts_index()

    def to_index_entries(self) -> List[tuple[int | None, int, str]]:
        """
        Return ordered (part, block, role) tuples mirroring the legacy INDEX file.
        Inline directions in role blocks emit a preceding _NARRATOR entry.
        """
        entries: List[tuple[int | None, int, str]] = []
        for block in self:
            part = block.block_id.part_id
            block_no = block.block_id.block_no
            if isinstance(block, RoleBlock):
                has_inline_dirs = any(isinstance(seg, DirectionSegment) for seg in block.segments)
                if has_inline_dirs:
                    entries.append((part, block_no, "_NARRATOR"))
                speaker_list = block.role_names if getattr(block, "role_names", None) else [block.primary_role]
                for role in speaker_list:
                    entries.append((part, block_no, role))
            else:
                entries.append((part, block_no, "_NARRATOR"))
        return entries

    def build_segment_maps(self) -> dict[str, dict[tuple[int | None, int], list[str]]]:
        """
        Build mapping role -> {(part, block): [segment_ids]} from in-memory blocks.
        Segment ids follow the underscore format used in audio filenames.
        """
        maps: dict[str, dict[tuple[int | None, int], list[str]]] = {}
        # Build from role blocks.
        for role in self.getRoles():
            maps[role.name] = role.segments()

        return maps


class PlayTextParser:
    """Parse a source play text file into a PlayText of Blocks."""

    def __init__(self, source_path: Path | None = None) -> None:
        # Prefer the normalized paragraphs file when available to align numbering
        self.source_path = source_path or paths.DEFAULT_PLAY

    def collapse_to_paragraphs(self, text: str) -> list[str]:
        """
        Join consecutive non-empty lines with spaces and use blank lines as
        paragraph boundaries, without emitting blank lines.
        """
        output: list[str] = []
        buffer: list[str] = []

        for raw_line in text.splitlines():
            # Treat any whitespace-only line as a boundary.
            if raw_line.strip():
                buffer.append(raw_line.strip())
            else:
                if buffer:
                    output.append(" ".join(buffer))
                    buffer.clear()

        if buffer:
            output.append(" ".join(buffer))

        return output

    def parse(self) -> Play:
        raw_text = self.source_path.read_text(encoding="utf-8-sig")
        paragraphs = self.collapse_to_paragraphs(raw_text)

        play = Play()
        current_part: int | None = None
        block_counter = 0
        meta_counters: dict[int | None, int] = {}

        for paragraph in paragraphs:
            if not paragraph:
                continue

            previous_block_counter = block_counter
            # Try each block type in order.
            parsed_block: Block | None = None
            for cls in (MetaBlock, DescriptionBlock, DirectionBlock, RoleBlock):
                block = cls.parse(paragraph, current_part, block_counter, meta_counters)
                if block is not None:
                    parsed_block = block
                    break

            if parsed_block is None:
                raise RuntimeError(f"Unable to parse paragraph into any block type: {paragraph}")

            play.append(parsed_block)
            play._by_id[parsed_block.block_id] = parsed_block
            current_part = parsed_block.block_id.part_id
            if isinstance(parsed_block, MetaBlock) and not parsed_block.text.startswith("##"):
                # Inline meta paragraphs should not advance the speech block counter.
                block_counter = previous_block_counter
            else:
                block_counter = parsed_block.block_id.block_no

        play.rebuild_parts_index()
        return play


class PlayTextEncoder:
    """Serialize PlayText back to paragraphs.txt format."""

    def __init__(self, output_path: Path | None = None) -> None:
        self.output_path = output_path or paths.PARAGRAPHS_PATH

    def encode(self, play: Play) -> None:
        lines: List[str] = []
        for block in play:
            if isinstance(block, MetaBlock):
                if block.text.startswith("##"):
                    lines.append(block.text)
                else:
                    lines.append(f"::{block.text}::")
            elif isinstance(block, DescriptionBlock):
                lines.append(f"[[{block.text}]]")
            elif isinstance(block, DirectionBlock):
                lines.append(f"_{block.text}_")
            elif isinstance(block, RoleBlock):
                speakers = block.role_names if getattr(block, "role_names", None) else [block.primary_role]
                if block.callout is None:
                    prefix = f"/{block.primary_role}."
                    lines.append(f"{prefix} {block.text}")
                elif block.callout and block.callout not in speakers:
                    roles = ",".join(speakers)
                    lines.append(f"{block.callout}/{block.primary_role}. {block.text}")
                elif len(speakers) > 1:
                    prefix = ". ".join(speakers) + "."
                    lines.append(f"{prefix} {block.text}")
                else:
                    lines.append(f"{block.primary_role}. {block.text}")
            else:
                raise RuntimeError(f"Unexpected block type during encoding: {type(block)}")
        content = "\n".join(lines) + ("\n" if lines else "")
        self.output_path.write_text(content, encoding="utf-8")
