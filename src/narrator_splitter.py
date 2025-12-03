#!/usr/bin/env python3
"""Split the narrator recording into per-line WAV snippets using PlayText."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List

from segment import Segment, DirectionSegment, SpeechSegment
from block import MetaBlock, DescriptionBlock, DirectionBlock, RoleBlock
from role_splitter import RoleSplitter


@dataclass
class NarratorSplitter(RoleSplitter):
    role: str = "_NARRATOR"

    def expected_ids(self, part_filter: str | None = None) -> List[str]:
        """Narrator-specific ids (includes meta/description/direction/inline narrator)."""
        segments: List[Segment] = []

        part_no: int | None | str
        if part_filter in (None, "", "_"):
            part_no = None if part_filter != "_" else "_"
        else:
            part_no = int(part_filter)

        for blk in self.play_text:
            if part_no == "_":
                if blk.block_id.part_id is not None:
                    continue
            elif isinstance(part_no, int):
                if blk.block_id.part_id != part_no:
                    continue

            if isinstance(blk, (MetaBlock, DescriptionBlock, DirectionBlock)):
                segments.extend(blk.segments)
            elif isinstance(blk, RoleBlock):
                for seg in blk.segments:
                    if isinstance(seg, SpeechSegment) and seg.role == "_NARRATOR":
                        segments.append(seg)
                    elif isinstance(seg, DirectionSegment):
                        segments.append(seg)
        return [str(seg.segment_id) for seg in segments]
