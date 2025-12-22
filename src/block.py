#!/usr/bin/env python3
"""Base Block type."""
from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List, Optional
import re

from block_id import BlockId
from segment_id import SegmentId
from segment import Segment, MetaSegment, DescriptionSegment, DirectionSegment, SpeechSegment, SimultaneousSegment
from segment_id import SegmentId

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
    ) -> "Block | None":
        """Attempt to parse paragraph; return a Block or None."""
        raise NotImplementedError

    @abstractmethod
    def _to_markdown(self, prefix: str | None) -> str:
        raise NotImplementedError
    
    def to_markdown(self, render_id=False) -> str:
        """Render the block back to text."""
        part = self.block_id.part_id if self.block_id.part_id is not None else ""
        id = f"{part}.{self.block_id.block_no}"
        prefix = f"{id} " if render_id else ""
        return self._to_markdown(prefix=prefix)
    

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

    def _to_markdown(self, prefix: str | None) -> str:
        return f"{prefix}{self.text}"
    
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
class RoleBlock(Block):
    PREFIX = ""
    SUFFIX = ""
    REGEX = re.compile(r"^(/?[A-Z][A-Z0-9 '()/:,-]*?)\.\s*(.*)$")
    MULTI_ROLE_RE = re.compile(r"^((?:[A-Z][A-Z0-9 '()-]*?\.\s*){2,})(.+)$")
    GROUP_ROLE_RE = re.compile(r"^([A-Z][A-Z0-9 '()-]*?)\s*\[(.+?)\]\s*[.:]?\s*(.*)$")
    ROLE_NAME_RE = re.compile(r"([A-Z][A-Z0-9 '()-]*?)\.\s*")
    NARRATION_RE = re.compile(r"(\(_.*?_\)(?:[.,?:;!](?![!?])|!(?![!?]))?)")
    INLINE_DIR_RE = re.compile(r"\(_.*?_\)")
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
        return roles

    @property
    def owner(self) -> str:
        return self.primary_role

    def owner_for_text(self, text: str) -> str:
        if text.startswith("(_"):
            return "_NARRATOR"
        return self.primary_role

    @classmethod
    def split_block_segments(cls, text: str, block_id: BlockId, role: str) -> List[Segment]:
        parts = cls.NARRATION_RE.split(text)
        segments: List[Segment] = []
        index = 1
        for i, part in enumerate(parts):
            speech = i % 2 == 0
            if speech:
                if part.strip():
                    segments.append(
                        SpeechSegment(
                            segment_id=SegmentId(block_id, index),
                            text=part.strip(),
                            role=role,
                        )
                    )
                    index += 1
            else: #narration
                segments.append(
                    DirectionSegment(
                        segment_id=SegmentId(block_id, index),
                        text=part.strip(),
                    )
                )
                index += 1
        return segments
    
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

        multi_match = cls.MULTI_ROLE_RE.match(paragraph)
        if multi_match:
            roles_chunk, speech = multi_match.groups()
            roles = [r.strip() for r in cls.ROLE_NAME_RE.findall(roles_chunk) if r.strip()]
            speech = speech.strip()
            if roles and speech:
                block_counter += 1
                block_id = BlockId(current_part, block_counter)
                segment = SimultaneousSegment(
                    segment_id=SegmentId(block_id, 1),
                    text=speech,
                    roles=roles,
                )
                block = cls(
                    block_id=block_id,
                    role_names=roles,
                    callout=roles[0],
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
            names = ",".join(speakers)
        return f"**{prefix}/{names}**: {self.text}"

    def to_markdown_for_role(self, role: str, prefix: str | None) -> str:
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
        return f"{prefix}**{names}**: {self.text}"
