#!/usr/bin/env python3
"""Data structures and parsing for play text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import re
from pathlib import Path
import paths
from block_id import BlockId
from segment import DirectionSegment, SpeechSegment, SimultaneousSegment
from block import Block, TitleBlock, DescriptionBlock, DirectionBlock, RoleBlock
import logging
from enum import Enum

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

@dataclass
class SourceTextMetadata:
    title: str = field(default='Untitled')
    subtitles: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    translators: list[str] = field(default_factory=list)
    source: Optional[str] = field(default=None)
    source_edition: Optional[str] = field(default=None) 
    source_url: Optional[str] = field(default=None)
    original_publication_year: Optional[str] = field(default=None)
    text_basis_year: Optional[str] = field(default=None)
    original_translation_year: Optional[str] = field(default=None)
    revised_translation_year: Optional[str] = field(default=None)

    @property
    def author(self):
        return self.authors[0] if self.authors else "Unknown Author"
    
@dataclass
class Reader:
    id: str
    reader: Optional[str] = field(default=None)
    role_name: Optional[str] = field(default=None)
    notes: Optional[str] = field(default=None)

@dataclass
class ReadingMetadata:
    target: str = field(default='librivox')
    reading_type: str = field(default='solo')
    readers: List[Reader] = field(default_factory=list)
    id_to_reader: Dict[str, Reader] = field(init=False)
    default_reader: Reader = field(init=False)

    def __post_init__(self):
        if self.solo_reading:
            if len(self.readers) > 1:
                raise RuntimeError("only one reader allowed for solo readings")
        if len(self.readers) == 0:
            self.readers.append(Reader(
                id="_DEFAULT",
                reader="Anonymous"))
        self.default_reader = next((r for r in self.readers if r.id == "_DEFAULT"), Reader(id="_DEFAULT", reader="Anonymous"))
        self.id_to_reader: Dict[str, Reader] = {} 
        for reader in self.readers:
            if reader.id in self.id_to_reader:
                raise RuntimeError(f"reader id {reader.id} is defined multiple times")
            if reader.id != "_DEFAULT":
                self.id_to_reader[reader.id] = reader                

    @property
    def solo_reading(self):
        return str(self.reading_type).strip().lower() in {'solo', 'solo reading'}

    @property
    def dramatic_reading(self):
        return str(self.reading_type).strip().lower() in {'dramatic', 'dramatic reading'}

    def reader_for_id(self, id: str):
        return self.id_to_reader.get(id) or self.default_reader
    
    
@dataclass
class Play:
    source_text_metadata: SourceTextMetadata = field(default_factory=SourceTextMetadata)
    reading_metadata: ReadingMetadata = field(default_factory=ReadingMetadata)
    blocks: List[Block] = field(default_factory=list)
    def __post_init__(self) -> None:
        self._by_id: dict[BlockId, Block] = {}
        for block in self.blocks:
            self._by_id[block.block_id] = block
        self._parts: dict[int | None, Part] = {}
        self._part_order: List[int | None] = []
        self._roles: dict[str, Role] = {}
        self._role_order: List[str] = []
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
        for blk in self.blocks:
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
    
    @property
    def author(self):
        return self.source_text_metadata.author
    
    @property
    def title(self):
        return self.source_text_metadata.title

    def block_for_id(self, block_id: BlockId) -> Block | None:
        """Return the Block for the given id, or None if not present."""
        return self._by_id.get(block_id)

    def _build_parts_index(self) -> None:
        heading_re = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
        self._parts.clear()
        self._part_order.clear()
        self._roles.clear()
        self._role_order.clear()
        for blk in self.blocks:
            pid = blk.block_id.part_id
            if pid not in self._parts:
                title: str | None = None
                if isinstance(blk, TitleBlock) and blk.text.startswith("##"):
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
        for block in self.blocks:
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


class PlayTextEncoder:
    """Serialize PlayText back to paragraphs.txt format."""

    def __init__(self, output_path: Path | None = None, paths_config: paths.PathConfig | None = None) -> None:
        self.paths = paths_config or paths.current()
        self.output_path = output_path or self.paths.paragraphs_path

    def encode(self, play: Play) -> None:
        lines: List[str] = []
        for block in play.blocks:
            if isinstance(block, TitleBlock):
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
