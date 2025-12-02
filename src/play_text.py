#!/usr/bin/env python3
"""Data structures and parsing for play text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from abc import ABC, abstractmethod
import re
from pathlib import Path

from paragraphs import collapse_to_paragraphs
from paths import DEFAULT_PLAY, PARAGRAPHS_PATH


@dataclass
class Title:
    part_no: int
    title: str


@dataclass
class BlockId:
    part_id: int | None
    block_no: int

    def nextId(self) -> "BlockId":
        """Return the next BlockId within the same part."""
        return BlockId(self.part_id, self.block_no + 1)

    def previousId(self) -> "BlockId | None":
        """Return the previous BlockId within the same part, or None if this is the first."""
        if self.block_no <= 0:
            return None
        return BlockId(self.part_id, self.block_no - 1)

    def __hash__(self) -> int:  # Ensure hashability for dict/set usage.
        return hash((self.part_id, self.block_no))


@dataclass
class SegmentId:
    block_id: BlockId
    segment_no: int


@dataclass
class Segment(ABC):
    segment_id: SegmentId
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass
class MetaSegment(Segment):
    pass


@dataclass
class DescriptionSegment(Segment):
    pass


@dataclass
class DirectionSegment(Segment):
    pass


@dataclass
class SpeechSegment(Segment):
    role: str

    def __str__(self) -> str:
        return f"{self.role}: {self.text}"


@dataclass
class Block(ABC):
    block_id: BlockId
    text: str
    segments: List[Segment] = field(default_factory=list)

    def __str__(self) -> str:
        return self.text

    @property
    def roles(self) -> List[str]:
        """Return roles associated with this block (default narrator)."""
        return ["_NARRATOR"]

    @property
    def owner(self) -> str:
        """Primary owner for this block (default narrator)."""
        return "_NARRATOR"

    def owner_for_text(self, text: str) -> str:
        """Owner for a given segment of text within this block."""
        return self.owner

    @classmethod
    @abstractmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        """Attempt to parse paragraph; return a Block or None."""
        raise NotImplementedError


@dataclass
class MetaBlock(Block):
    PREFIX = "::"
    SUFFIX = "::"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}(.*){re.escape(SUFFIX)}$")

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        heading = re.match(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$", paragraph)
        if heading:
            new_part = int(heading.group(1))
            block_id = BlockId(new_part, 0)
            block = cls(
                block_id=block_id,
                text=paragraph,
                segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text=paragraph)],
            )
            return block

        meta_match = cls.REGEX.match(paragraph)
        if meta_match:
            meta_counters[current_part] = meta_counters.get(current_part, 0) + 1
            block_id = BlockId(current_part, meta_counters[current_part])
            text = meta_match.group(1).strip()
            block = cls(
                block_id=block_id,
                text=text,
                segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text=text)],
            )
            return block

        return None


@dataclass
class DescriptionBlock(Block):
    PREFIX = "[["
    SUFFIX = "]]"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}(.*){re.escape(SUFFIX)}$")

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        match = cls.REGEX.match(paragraph)
        if not match:
            return None
        block_counter += 1
        block_id = BlockId(current_part, block_counter)
        text = match.group(1).strip()
        block = cls(
            block_id=block_id,
            text=text,
            segments=[DescriptionSegment(segment_id=SegmentId(block_id, 1), text=text)],
        )
        return block


@dataclass
class DirectionBlock(Block):
    PREFIX = "_"
    SUFFIX = "_"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}+(.*?){re.escape(SUFFIX)}+\s*$")

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        match = cls.REGEX.match(paragraph)
        if not match:
            return None
        block_counter += 1
        block_id = BlockId(current_part, block_counter)
        text = match.group(1).strip()
        block = cls(
            block_id=block_id,
            text=text,
            segments=[DirectionSegment(segment_id=SegmentId(block_id, 1), text=text)],
        )
        return block


@dataclass
class RoleBlock(Block):
    PREFIX = ""
    SUFFIX = ""
    REGEX = re.compile(r"^([A-Z][A-Z '()-]*?)\.\s*(.*)$")
    INLINE_DIR_RE = re.compile(r"\(_.*?_\)")
    role: str = ""
    segments: List[Segment] = field(default_factory=list)

    def __str__(self) -> str:
        if self.segments:
            return " ".join(str(s) for s in self.segments)
        return f"{self.role}: {self.text}"

    @property
    def roles(self) -> List[str]:
        has_inline_dirs = any(isinstance(seg, DirectionSegment) for seg in self.segments)
        roles: List[str] = ["_NARRATOR"] if has_inline_dirs else []
        roles.append(self.role)
        return roles

    @property
    def owner(self) -> str:
        return self.role

    def owner_for_text(self, text: str) -> str:
        if text.startswith("(_"):
            return "_NARRATOR"
        return self.role

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        role_match = cls.REGEX.match(paragraph)
        if not role_match:
            return None
        role, speech = role_match.groups()
        block_counter += 1
        block_id = BlockId(current_part, block_counter)
        speech = speech.strip()
        segments: List[Segment] = []
        last_end = 0
        seg_no = 1
        for match in cls.INLINE_DIR_RE.finditer(speech):
            pre = speech[last_end : match.start()]
            if pre.strip():
                segments.append(SpeechSegment(segment_id=SegmentId(block_id, seg_no), text=pre.strip(), role=role))
                seg_no += 1

            direction = match.group(0).strip()
            punct_end = match.end()
            trailing_punct = ""
            while punct_end < len(speech) and speech[punct_end] in ".,;:!?":
                trailing_punct += speech[punct_end]
                punct_end += 1

            if direction:
                segments.append(DirectionSegment(segment_id=SegmentId(block_id, seg_no), text=direction))
                seg_no += 1
                if trailing_punct:
                    segments.append(DirectionSegment(segment_id=SegmentId(block_id, seg_no), text=trailing_punct))
                    seg_no += 1
            last_end = punct_end

        tail = speech[last_end:]
        if tail.strip():
            segments.append(SpeechSegment(segment_id=SegmentId(block_id, seg_no), text=tail.strip(), role=role))

        if not segments:
            segments.append(SpeechSegment(segment_id=SegmentId(block_id, 1), text=speech.strip(), role=role))
        block = cls(
            block_id=block_id,
            role=role,
            text=speech.strip(),
            segments=segments,
        )
        return block


@dataclass
class Part:
    """A collection of blocks belonging to a part."""

    part_no: int | None
    title: str | None
    blocks: List[Block] = field(default_factory=list)


class PlayText(List[Block]):
    def __init__(self, items: List[Block] | None = None) -> None:
        super().__init__(items or [])
        self._by_id: dict[BlockId, Block] = {}
        for block in self:
            self._by_id[block.block_id] = block
        self._parts: dict[int | None, Part] = {}
        self._part_order: List[int | None] = []
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
                if not include_meta_roles and blk.role.startswith("_"):
                    continue
                roles.append(blk.role)
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

    def getPart(self, part_id: int | None) -> Part | None:
        """Return the Part object for the given id."""
        if not self._parts:
            self._build_parts_index()
        return self._parts.get(part_id)

    def getParts(self) -> List[Part]:
        """Return all Part objects in play order."""
        if not self._parts:
            self._build_parts_index()
        return [self._parts[pid] for pid in self._part_order]

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
                entries.append((part, block_no, block.role))
            else:
                entries.append((part, block_no, "_NARRATOR"))
        return entries

    def build_segment_maps(self) -> dict[str, dict[tuple[int | None, int], list[str]]]:
        """
        Build mapping role -> {(part, block): [segment_ids]} from in-memory blocks.
        Segment ids follow the underscore format used in audio filenames.
        """
        maps: dict[str, dict[tuple[int | None, int], list[str]]] = {}
        for blk in self:
            part = blk.block_id.part_id
            block_no = blk.block_id.block_no
            key = (part, block_no)
            for seg in blk.segments:
                if isinstance(seg, SpeechSegment):
                    role = seg.role
                else:
                    role = "_NARRATOR"
                seg_id = f"{'' if part is None else part}_{block_no}_{seg.segment_id.segment_no}"
                maps.setdefault(role, {}).setdefault(key, []).append(seg_id)
        return maps


class PlayTextParser:
    """Parse a source play text file into a PlayText of Blocks."""

    def __init__(self, source_path: Path | None = None) -> None:
        # Prefer the normalized paragraphs file when available to align numbering
        self.source_path = source_path or (PARAGRAPHS_PATH if PARAGRAPHS_PATH.exists() else DEFAULT_PLAY)

    def parse(self) -> PlayText:
        raw_text = self.source_path.read_text(encoding="utf-8-sig")
        if self.source_path == PARAGRAPHS_PATH:
            # paragraphs.txt is already normalized to one paragraph per line
            paragraphs = [line.strip() for line in raw_text.splitlines() if line.strip()]
        else:
            paragraphs = collapse_to_paragraphs(raw_text)

        play = PlayText()
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
                # Ignore unrecognized paragraphs to stay aligned with existing block numbering.
                continue

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
        self.output_path = output_path or PARAGRAPHS_PATH

    def encode(self, play: PlayText) -> None:
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
                lines.append(f"{block.role}. {block.text}")
            else:
                raise RuntimeError(f"Unexpected block type during encoding: {type(block)}")
        content = "\n".join(lines) + ("\n" if lines else "")
        self.output_path.write_text(content, encoding="utf-8")
