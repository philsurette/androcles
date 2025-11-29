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


class PlayText(List[Block]):
    def __init__(self, items: List[Block] | None = None) -> None:
        super().__init__(items or [])


class PlayTextParser:
    """Parse a source play text file into a PlayText of Blocks."""

    def __init__(self, source_path: Path | None = None) -> None:
        self.source_path = source_path or DEFAULT_PLAY

    def parse(self) -> PlayText:
        raw_text = self.source_path.read_text(encoding="utf-8-sig")
        paragraphs = collapse_to_paragraphs(raw_text)

        play = PlayText()
        current_part: int | None = None
        block_counter = 0
        meta_counters: dict[int | None, int] = {}

        for paragraph in paragraphs:
            if not paragraph:
                continue

            # Try each block type in order.
            parsed_block: Block | None = None
            for cls in (MetaBlock, DescriptionBlock, DirectionBlock, RoleBlock):
                block = cls.parse(paragraph, current_part, block_counter, meta_counters)
                if block is not None:
                    parsed_block = block
                    break

            if parsed_block is None:
                # Fallback: treat as a direction block.
                block_counter += 1
                block_id = BlockId(current_part, block_counter)
                text = paragraph.strip()
                parsed_block = DirectionBlock(
                    block_id=block_id,
                    text=text,
                    segments=[DirectionSegment(segment_id=SegmentId(block_id, 1), text=text)],
                )

            play.append(parsed_block)
            current_part = parsed_block.block_id.part_id
            block_counter = parsed_block.block_id.block_no

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
