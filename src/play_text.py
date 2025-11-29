#!/usr/bin/env python3
"""Data structures and parsing for play text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from abc import ABC
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


@dataclass
class MetaBlock(Block):
    PREFIX = "::"
    SUFFIX = "::"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}(.*){re.escape(SUFFIX)}$")


@dataclass
class DescriptionBlock(Block):
    PREFIX = "[["
    SUFFIX = "]]"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}(.*){re.escape(SUFFIX)}$")


@dataclass
class DirectionBlock(Block):
    PREFIX = "_"
    SUFFIX = "_"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}+(.*?){re.escape(SUFFIX)}+\s*$")


@dataclass
class RoleBlock(Block):
    PREFIX = ""
    SUFFIX = ""
    REGEX = re.compile(r"^([A-Z][A-Z '()-]*?)\.\s*(.*)$")
    role: str
    segments: List[Segment] = field(default_factory=list)

    def __str__(self) -> str:
        if self.segments:
            return " ".join(str(s) for s in self.segments)
        return f"{self.role}: {self.text}"


class PlayText(List[Block]):
    def __init__(self, items: List[Block] | None = None) -> None:
        super().__init__(items or [])


class SegmentParser:
    """Parse raw speech into typed segments."""

    INLINE_DIR_RE = re.compile(r"\(_.*?_\)")

    def parse_role_segments(self, role: str, block_id: BlockId, speech: str) -> List[Segment]:
        segments: List[Segment] = []
        last_end = 0
        seg_no = 1

        for match in self.INLINE_DIR_RE.finditer(speech):
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

        return segments


class PlayTextParser:
    """Parse a source play text file into a PlayText of Blocks."""

    def __init__(self, source_path: Path | None = None) -> None:
        self.source_path = source_path or DEFAULT_PLAY
        self.segment_parser = SegmentParser()

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

            part_match = PART_HEADING_RE.match(paragraph)
            if part_match:
                current_part = int(part_match.group(1))
                block_counter = 0
                block_id = BlockId(current_part, 0)
                play.append(
                    MetaBlock(
                        block_id=block_id,
                        text=paragraph,
                        segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text=paragraph)],
                    )
                )
                continue

            # Meta
            meta_match = MetaBlock.REGEX.match(paragraph)
            if meta_match:
                meta_counters[current_part] = meta_counters.get(current_part, 0) + 1
                block_id = BlockId(current_part, meta_counters[current_part])
                text = meta_match.group(1).strip()
                play.append(
                    MetaBlock(
                        block_id=block_id,
                        text=text,
                        segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text=text)],
                    )
                )
                continue

            # Description
            desc_match = DescriptionBlock.REGEX.match(paragraph)
            if desc_match:
                block_counter += 1
                block_id = BlockId(current_part, block_counter)
                text = desc_match.group(1).strip()
                play.append(
                    DescriptionBlock(
                        block_id=block_id,
                        text=text,
                        segments=[DescriptionSegment(segment_id=SegmentId(block_id, 1), text=text)],
                    )
                )
                continue

            # Stage direction
            stage_match = DirectionBlock.REGEX.match(paragraph)
            if stage_match:
                block_counter += 1
                block_id = BlockId(current_part, block_counter)
                text = stage_match.group(1).strip()
                play.append(
                    DirectionBlock(
                        block_id=block_id,
                        text=text,
                        segments=[DirectionSegment(segment_id=SegmentId(block_id, 1), text=text)],
                    )
                )
                continue

            # Role speech
            role_match = RoleBlock.REGEX.match(paragraph)
            if role_match:
                role, speech = role_match.groups()
                block_counter += 1
                block_id = BlockId(current_part, block_counter)
                segments = self.segment_parser.parse_role_segments(role, block_id, speech.strip())
                play.append(
                    RoleBlock(
                        block_id=block_id,
                        role=role,
                        text=speech.strip(),
                        segments=segments,
                    )
                )
                continue

            # Fallback: treat as description to make unexpected format visible.
            block_counter += 1
            block_id = BlockId(current_part, block_counter)
            text = paragraph.strip()
            play.append(
                DescriptionBlock(
                    block_id=block_id,
                    text=text,
                    segments=[DescriptionSegment(segment_id=SegmentId(block_id, 1), text=text)],
                )
            )

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
