#!/usr/bin/env python3
"""
Split the narrator recording into per-line WAV snippets using PlayText.

Naming:
- With part id: <part>_<block>_<elem>.wav
- Without part id (preamble/meta): _<block>_<elem>.wav

Only inline directions are kept from mixed speech blocks; pure description/meta/direction
entries keep all bullet lines.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from dataclasses import dataclass
import logging
from typing import List

from audio_splitter import AudioSplitter
from play_text import (
    PlayText,
    SpeechSegment,
)
from segment import Segment, DirectionSegment, SpeechSegment
from block import MetaBlock, DescriptionBlock, DirectionBlock, RoleBlock
from paths import RECORDINGS_DIR, SEGMENTS_DIR


@dataclass
class NarratorSplitter:
    play_text: PlayText
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    pad_end_ms: int = 200
    chunk_size: int = 50
    detection_chunk_ms: int | None = None
    verbose: bool = False
    chunk_exports: bool = False
    chunk_export_size: int = 25
    use_silence_window: bool = False

    def assemble_segments(self, part_filter: str | None = None) -> List[Segment]:
        """Return ordered narrator/meta segments from the PlayText."""
        segments: List[Segment] = []

        part_no: int | None | str
        if part_filter in (None, "", "_"):
            part_no = None if part_filter != "_" else "_"
        else:
            try:
                part_no = int(part_filter)
            except ValueError:
                part_no = None

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
        return segments

    @staticmethod
    def _segment_id_str(seg: Segment) -> str:
        block = seg.segment_id.block_id
        return f"{'' if block.part_id is None else block.part_id}_{block.block_no}_{seg.segment_id.segment_no}"

    def split(self, part_filter: str | None = None) -> None:
        src_path = RECORDINGS_DIR / "_NARRATOR.wav"
        if not src_path.exists():
            print(f"Narrator recording not found: {src_path}", file=sys.stderr)
            sys.exit(1)

        #logging.info("Processing narrator from %s", src_path)
        pf = "" if part_filter == "_" else part_filter
        expected_segments = self.assemble_segments(part_filter=pf)
        splitter = AudioSplitter(
            min_silence_ms=self.min_silence_ms,
            silence_thresh=self.silence_thresh,
            pad_end_ms=self.pad_end_ms,
            chunk_size=self.chunk_size,
            verbose=self.verbose,
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )
        spans = splitter.detect_spans(
            src_path, chunk_duration_ms=self.detection_chunk_ms if self.use_silence_window else None
        )
        splitter.export_spans(
            src_path,
            spans,
            [self._segment_id_str(seg) for seg in expected_segments],
            SEGMENTS_DIR / "_NARRATOR",
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )

        logger = logging.getLogger(__name__)
        total_time = splitter.last_detect_seconds + splitter.last_export_seconds
        if len(spans) != len(expected_segments):
            logger.warning(
                "⚠️ split %3d/%-3d in %4.1fs %s",
                len(spans),
                len(expected_segments),
                total_time,
                os.path.relpath(str(src_path), str(Path.cwd())),
            )
        else:
            logger.info(
                "✅ split %3d/%-3d in %4.1fs %s",
                len(spans),
                len(expected_segments),
                total_time,
                os.path.relpath(str(src_path), str(Path.cwd())),
            )
        return total_time


