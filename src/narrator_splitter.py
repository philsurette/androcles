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

import argparse
import sys
from dataclasses import dataclass
import logging
from typing import List

from audio_splitter import AudioSplitter
from play_text import (
    PlayText,
    PlayTextParser,
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

    def split(self, part_filter: str | None = None) -> float | None:
        src_path = RECORDINGS_DIR / "_NARRATOR.wav"
        if not src_path.exists():
            print(f"Narrator recording not found: {src_path}", file=sys.stderr)
            sys.exit(1)

        logging.info("Processing narrator from %s", src_path)
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
                "⚠️  Narrator split mismatch: expected %d snippets, got %d (silence detect %.3fs, export %.3fs)",
                len(expected_segments),
                len(spans),
                splitter.last_detect_seconds,
                splitter.last_export_seconds,
            )
        else:
            logger.info(
                "✅  Split narrator into %d snippets in %.0fs (silence detect %.3fs, export %.3fs)",
                len(spans),
                total_time,
                splitter.last_detect_seconds,
                splitter.last_export_seconds,
            )
        return total_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Split narrator recording into per-line WAV snippets.")
    parser.add_argument("--min-silence-ms", type=int, default=1700, help="Silence length (ms) to split on (default 1700)")
    parser.add_argument("--silence-thresh", type=int, default=-45, help="Silence threshold dBFS (default -45)")
    parser.add_argument("--pad-end-ms", type=int, default=200, help="Pad each segment end by this many ms (default 200)")
    parser.add_argument("--part", help="Limit to a specific part id, or '_' for no-part entries")
    parser.add_argument("--chunk-size", type=int, default=50, help="Chunk size (ms) for silence detection")
    parser.add_argument(
        "--detect-chunk-ms",
        type=int,
        default=0,
        help="Process silence detection in windows of this size (ms). Use 0 to scan whole file.",
    )
    parser.add_argument("--verbose", action="store_true", help="Log ffmpeg commands used for splitting")
    parser.add_argument("--chunk-exports", action="store_true", help="Export in batches instead of one ffmpeg call")
    parser.add_argument("--chunk-export-size", type=int, default=25, help="Batch size when chunking exports")
    parser.add_argument(
        "--use-silence-window",
        action="store_true",
        help="Enable windowed silence detection; when off, scans the whole file at once",
    )
    parser.add_argument(
        "--silence-window-size-seconds",
        type=int,
        default=300,
        help="Window size in seconds for silence detection when windowing is enabled",
    )
    args = parser.parse_args()
    play_text = PlayTextParser().parse()
    NarratorSplitter(
        play_text=play_text,
        min_silence_ms=args.min_silence_ms,
        silence_thresh=args.silence_thresh,
        pad_end_ms=args.pad_end_ms,
        chunk_size=args.chunk_size,
        detection_chunk_ms=(
            args.silence_window_size_seconds * 1000 if args.use_silence_window else (args.detect_chunk_ms or None)
        ),
        verbose=args.verbose,
        chunk_exports=args.chunk_exports,
        chunk_export_size=args.chunk_export_size,
        use_silence_window=args.use_silence_window,
    ).split(part_filter=args.part)


if __name__ == "__main__":
    main()
