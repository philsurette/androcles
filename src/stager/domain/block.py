#!/usr/bin/env python3
"""Base Block type."""
from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List, Optional
import re

from stager.domain.block_id import BlockId
from stager.domain.segment_id import SegmentId
from stager.domain.segment import Segment, MetaSegment, DescriptionSegment, DirectionSegment, BlockingSegment, SpeechSegment, SimultaneousSegment

@dataclass
class Block(ABC):
    block_id: BlockId
    text: str
    segments: List[Segment] = field(default_factory=list)
    production_id: str | None = field(default=None, kw_only=True)
    content_hash: str | None = field(default=None, kw_only=True)

    def __str__(self) -> str:
        return self.text

    @property
    def roles(self) -> List[str]:
        """Return roles associated with this block (default narrator)."""
        return ["_NARRATOR"]

    @classmethod
    @abstractmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> "Block | None":
        """Attempt to parse paragraph; return a Block or None."""
        raise NotImplementedError

    @abstractmethod
    def _to_markdown(self, prefix: str | None) -> str:
        raise NotImplementedError
    
    def to_markdown(self, render_id=False, prefix: str | None = None) -> str:
        """Render the block back to text."""
        if prefix is None:
            part = self.block_id.part_id if self.block_id.part_id is not None else ""
            id = f"{part}.{self.block_id.block_no}"
            prefix = f"{id} " if render_id else ""
        return self._to_markdown(prefix=prefix)
    

@dataclass
class TitleBlock(Block):
    PREFIX = "::"
    SUFFIX = "::"
    REGEX = re.compile(fr"^{re.escape(PREFIX)}(.*){re.escape(SUFFIX)}$")
    
    part_id: int = -1
    heading: str = ""

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        match = re.match(r"^##\s*(?P<part>\d+)\s*[:.]\s*(?P<heading>.*?)\s*##$", paragraph)
        if match:
            part_id = int(match.groupdict()['part'])
            heading = match.groupdict()['heading']
            block_id = BlockId(part_id, 0)
            block = cls(
                block_id=block_id,
                text=paragraph,
                segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text=paragraph)],
                part_id=part_id,
                heading=heading
            )
            return block
        return None
    
    def _to_markdown(self, prefix: str | None) -> str:
        return f"{prefix}{self.heading}"
    
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

    def _to_markdown(self, prefix: str | None) -> str:
        return f"""```
{prefix}{self.text}
```"""


@dataclass
class DirectionBlock(Block):
    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        if not paragraph.startswith("__"):
            return None
        block_counter += 1
        block_id = BlockId(current_part, block_counter)
        text = paragraph.strip("_")
        block = cls(
            block_id=block_id,
            text=text,
            segments=[DirectionSegment(segment_id=SegmentId(block_id, 1), text=text)],
        )
        return block
    
    def _to_markdown(self, prefix: str | None) -> str:
        return f"{prefix}*{self.text}*"

@dataclass
class BlockingBlock(Block):
    targets: List[str] = field(default_factory=list)
    placement: str = "before"

    @property
    def roles(self) -> List[str]:
        return [] if "*" in self.targets else list(self.targets)

    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        return None

    def _to_markdown(self, prefix: str | None) -> str:
        return f"{prefix}/{', '.join(self.targets)}: {self.text}"

@dataclass
class RoleBlock(Block):
    PREFIX = ""
    SUFFIX = ""
    REGEX = re.compile(r"^(/?[A-Z][A-Z0-9 '()/:,-]*?)\.\s*(.*)$")
    GROUP_ROLE_RE = re.compile(r"^([A-Z][A-Z0-9 '()-]*?)\s*\[(.+?)\]\s*[.:]?\s*(.*)$")
    NARRATION_RE = re.compile(r"(\(_.*?_\)(?:[.,?:;!](?![!?])|!(?![!?]))?)")
    INLINE_DIR_RE = re.compile(r"\(_.*?_\)")
    INLINE_BLOCKING_RE = re.compile(r"^\(_/(?P<targets>[^:]+):\s*(?P<text>.*?)_\)(?P<trailing>[.,?:;!])?$")
    role_names: List[str] = field(default_factory=list)
    callout: Optional[str] = None
    segments: List[Segment] = field(default_factory=list)

    def __str__(self) -> str:
        if self.segments:
            return " ".join(str(s) for s in self.segments)
        else:
            prefix = f"{self.callout}/" if self.callout is not None else "/"
            roles = ",".join(self.role_names)
            return f"{prefix}{roles}: {self.text}"

    @property
    def primary_role(self) -> str:
        return self.role_names[0] if self.role_names else "_NARRATOR"

    @property
    def roles(self) -> List[str]:
        has_inline_dirs = any(isinstance(seg, DirectionSegment) for seg in self.segments)
        roles: List[str] = ["_NARRATOR"] if has_inline_dirs else []
        roles.extend(self.role_names)
        for segment in self.segments:
            if isinstance(segment, BlockingSegment):
                roles.extend(target for target in segment.targets if target != "*")
        roles = list(dict.fromkeys(roles))
        return roles

    @classmethod
    def split_block_segments(cls, text: str, block_id: BlockId, role: str) -> List[Segment]:
        parts = cls.NARRATION_RE.split(text)
        segments: List[Segment] = []
        pending_speech_parts: List[str] = []
        pending_blocking: List[BlockingSegment] = []
        index = 1

        def flush_speech() -> None:
            nonlocal index
            speech_text = " ".join(part.strip() for part in pending_speech_parts if part.strip())
            pending_speech_parts.clear()
            if not speech_text:
                return
            segments.append(
                SpeechSegment(
                    segment_id=SegmentId(block_id, index),
                    text=speech_text,
                    role=role,
                )
            )
            index += 1

        def flush_blocking() -> None:
            nonlocal index
            while pending_blocking:
                segment = pending_blocking.pop(0)
                segment.segment_id = SegmentId(block_id, index)
                segments.append(segment)
                index += 1

        for i, part in enumerate(parts):
            speech = i % 2 == 0
            if speech:
                if part.strip():
                    pending_speech_parts.append(part)
            else: #narration
                blocking_segment = cls._blocking_segment(part.strip(), block_id, index)
                if blocking_segment is not None:
                    pending_blocking.append(blocking_segment)
                else:
                    flush_speech()
                    flush_blocking()
                    segments.append(
                        DirectionSegment(
                            segment_id=SegmentId(block_id, index),
                            text=part.strip(),
                        )
                    )
                    index += 1
        flush_speech()
        flush_blocking()
        return segments

    @classmethod
    def _blocking_segment(cls, text: str, block_id: BlockId, index: int) -> BlockingSegment | None:
        match = cls.INLINE_BLOCKING_RE.match(text)
        if match is None:
            return None
        targets = [target.strip() for target in match.group("targets").split(",") if target.strip()]
        return BlockingSegment(
            segment_id=SegmentId(block_id, index),
            text=match.group("text").strip(),
            targets=targets,
        )
    
    @classmethod
    def parse(
        cls,
        paragraph: str,
        current_part: int | None,
        block_counter: int,
        meta_counters: dict[int | None, int],
    ) -> Block | None:
        grouped_match = cls.GROUP_ROLE_RE.match(paragraph)
        if grouped_match:
            group_role, raw_roles, speech = grouped_match.groups()
            roles = [r.strip() for r in raw_roles.split(",") if r.strip()]
            speech = speech.strip()
            if not speech:
                return None
            block_counter += 1
            block_id = BlockId(current_part, block_counter)
            segment = SimultaneousSegment(
                segment_id=SegmentId(block_id, 1),
                text=speech,
                roles=roles if roles else [group_role],
            )
            block = cls(
                block_id=block_id,
                role_names=roles if roles else [group_role],
                callout=group_role,
                text=speech,
                segments=[segment],
            )
            return block

        role_match = cls.REGEX.match(paragraph)
        if not role_match:
            return None
        raw_prefix, speech = role_match.groups()
        block_counter += 1
        block_id = BlockId(current_part, block_counter)
        speech = speech.strip()

        # Support callout_name/role_name, /role_name (no callout), or plain role.
        callout_val: Optional[str]
        role_part: str
        if "/" in raw_prefix:
            callout_part, role_part = raw_prefix.split("/", 1)
            callout_val = callout_part or None
        elif raw_prefix.startswith("/"):
            callout_val = None
            role_part = raw_prefix.lstrip("/")
        else:
            callout_val = raw_prefix
            role_part = raw_prefix

        role_names = [r.strip() for r in role_part.split(",") if r.strip()]
        if not role_names:
            return None

        if len(role_names) > 1:
            segment = SimultaneousSegment(
                segment_id=SegmentId(block_id, 1),
                text=speech,
                roles=role_names,
            )
            block = cls(
                block_id=block_id,
                role_names=role_names,
                callout=callout_val,
                text=speech,
                segments=[segment],
            )
            return block

        block = cls(
            block_id=block_id,
            role_names=role_names,
            callout=callout_val,
            text=speech.strip(),
            segments=cls.split_block_segments(speech, block_id, role_names[0]),
        )
        return block

    def _to_markdown(self, prefix: str | None) -> str:
        speakers = ",".join(self.role_names)
        if self.callout is None:
            # Explicitly suppress callout; show leading slash.
            names = f"/{speakers}"
        elif self.callout and self.callout not in speakers:
            # Distinct callout and primary role.
            names = f"{self.callout}/{speakers}"
        else:
            names = speakers
        return f"{prefix}**{names}**: {self.text}"

    def to_markdown_for_role(self, role: str, prefix: str | None, include_blocking: bool = True) -> str:
        """
        Render markdown labeling with the provided role (for role-specific views).
        Uses the block's callout if present; otherwise suppresses with '/' prefix.
        """
        if self.callout is None:
            names = f"/{role}"
        elif self.callout and self.callout != role:
            names = f"{self.callout}/{role}"
        else:
            names = role
        text = self.text if include_blocking else self._text_without_inline_blocking()
        return f"{prefix}**{names}**: {text}"

    def _text_without_inline_blocking(self) -> str:
        return re.sub(r"\s*\(_/[^:]+:\s*.*?_\)", "", self.text).strip()
