#!/usr/bin/env python3
"""Callout director strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from pydub import AudioSegment


from clip import CalloutClip
from paths import CALLOUTS_DIR
from play_text import PlayText, BlockId, RoleBlock, DirectionSegment


class CalloutDirector(ABC):
    """Base class for callout decision logic."""

    def __init__(self, play_text: PlayText) -> None:
        self.play_text = play_text

    @abstractmethod
    def calloutForBlock(self, block_id: BlockId) -> Optional[CalloutClip]:
        """Return the callout clip for a given block, or None."""
        raise NotImplementedError

    def _load_length_ms(self, path: Path) -> int:
        return len(AudioSegment.from_file(path))


    def _find_block(self, block_id: BlockId) -> Optional[RoleBlock]:
        for blk in self.play_text:
            if blk.block_id.part_id == block_id.part_id and blk.block_id.block_no == block_id.block_no:
                if isinstance(blk, RoleBlock):
                    return blk
        return None


class NoCalloutDirector(CalloutDirector):
    """Never emit callouts."""

    def calloutForBlock(self, block_id: BlockId) -> Optional[CalloutClip]:
        return None


class RoleCalloutDirector(CalloutDirector):
    """Emit callouts for every role block."""

    def calloutForBlock(self, block_id: BlockId) -> Optional[CalloutClip]:
        block = self._find_block(block_id)
        if block is None:
            return None
        path = CALLOUTS_DIR / f"{block.role}_callout.wav"
        length_ms = self._load_length_ms(path)
        return CalloutClip(
            path=path,
            text="",
            role="_NARRATOR",
            clip_id=block.role,
            length_ms=length_ms,
            offset_ms=0,
        )


class ConversationAwareCalloutDirector(CalloutDirector):
    """
    Emit callouts based on conversation flow:
      i) callout if the role block begins with an inline direction
      ii) callout if the role is one of the first two roles in the part
      iii) callout if the role differs from both of the last two roles in this part
    """

    def __init__(self, play_text: PlayText) -> None:
        super().__init__(play_text)

    def calloutForBlock(self, block_id: BlockId) -> Optional[CalloutClip]:
        block = self._find_block(block_id)
        if block is None:
            return None

        starts_with_direction = bool(block.segments and isinstance(block.segments[0], DirectionSegment))
        last_two = self.play_text.getPrecedingRoles(block_id, num_preceding=2, limit_to_current_part=True)
        is_first_two = len(last_two) < 2
        is_new_speaker = block.role not in last_two

        need_callout = starts_with_direction or is_first_two or is_new_speaker

        if not need_callout:
            return None

        path = CALLOUTS_DIR / f"{block.role}_callout.wav"
        length_ms = self._load_length_ms(path)
        return CalloutClip(
            path=path,
            text="",
            role="_NARRATOR",
            clip_id=block.role,
            length_ms=length_ms,
            offset_ms=0,
        )
