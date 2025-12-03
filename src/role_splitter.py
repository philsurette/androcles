#!/usr/bin/env python3
"""
Split role recordings into per-line mp3 snippets based on the role blocks.

Assumptions:
- Input recordings live in plays/.../recordings/<ROLE>.mp3 (exclude names starting with "_").
- Output snippets are written to build/audio/<ROLE>/, named <part>_<block>_<elem>.mp3
  where elem counts all bullet lines in the block (directions included) but only
  speech lines (non-directions) are expected in the role recording.
- Snippets are separated by ~2s of silence; adjust thresholds via CLI flags if needed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from dataclasses import dataclass, field

from audio_splitter import AudioSplitter
from paths import SEGMENTS_DIR, RECORDINGS_DIR
from play_text import PlayText, PlayTextParser, RoleBlock, SpeechSegment


@dataclass
class RoleSplitter:
    play_text: PlayText
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    chunk_size: int = 50
    pad_end_ms: int = 200
    verbose: bool = False
    chunk_exports: bool = False
    chunk_export_size: int = 100
    splitter: AudioSplitter = field(default_factory=AudioSplitter)

    def __post_init__(self) -> None:
        if self.play_text is None:
            raise ValueError("play_text is required for RoleSplitter")
        # Sync splitter thresholds
        self.splitter.min_silence_ms = self.min_silence_ms
        self.splitter.silence_thresh = self.silence_thresh
        self.splitter.chunk_size = self.chunk_size
        self.splitter.pad_end_ms = self.pad_end_ms
        self.splitter.verbose = self.verbose
        self.splitter.chunk_exports = self.chunk_exports
        self.splitter.chunk_export_size = self.chunk_export_size

    def expected_ids(self, role: str, part_filter: str | None = None) -> List[str]:
        """
        Return expected segment ids for speech lines of a role, optionally filtered by part.
        Uses in-memory PlayText blocks (directions counted for numbering, only speech for the role emits ids).
        """
        ids: List[str] = []
        role_obj = self.play_text.getRole(role)
        if role_obj is None:
            logging.warning("Role %s not found in play text", role)
            return ids

        blocks: List[RoleBlock] = role_obj.getBlocks(int(part_filter) if part_filter is not None else None)
        for blk in blocks:
            seq = 0
            for seg in blk.segments:
                text = getattr(seg, "text", "").strip()
                if not text:
                    continue
                # Ignore trivial punctuation (but keep expressive cries like "!!!" or "?!?").
                if text in {".", ",", ":", ";"}:
                    continue
                seq += 1
                if isinstance(seg, SpeechSegment) and seg.role == role:
                    ids.append(
                        f"{'' if blk.block_id.part_id is None else blk.block_id.part_id}_{blk.block_id.block_no}_{seq}"
                    )
        return ids

    def process_role(self, role: str, part_filter: str | None = None) -> None:
        src_path = self.splitter.find_recording(role)
        if not src_path:
            print(f"Recording not found for role {role}", file=sys.stderr)
            return

        logging.info("Processing role %s from %s", role, src_path)
        expected_ids = self.expected_ids(role, part_filter=part_filter)
        spans = self.splitter.detect_spans(src_path)
        self.splitter.export_spans(
            src_path,
            spans,
            expected_ids,
            SEGMENTS_DIR / role,
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )

        if len(spans) != len(expected_ids):
            print(f"WARNING {role}: expected {len(expected_ids)} snippets, got {len(spans)}")
        else:
            print(f"{role}: split {len(spans)} snippets OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split role recordings into per-line mp3 snippets.")
    parser.add_argument(
        "--role",
        help="Role name to process (default: all recordings in plays/.../recordings excluding leading underscore).",
    )
    parser.add_argument("--min-silence-ms", type=int, default=1700, help="Silence length (ms) to split on (default 1700)")
    parser.add_argument("--silence-thresh", type=int, default=-45, help="Silence threshold dBFS (default -45)")
    parser.add_argument("--verbose", action="store_true", help="Log ffmpeg commands used for splitting")
    parser.add_argument("--chunk-exports", action="store_true", help="Export in batches instead of one ffmpeg call")
    parser.add_argument("--chunk-export-size", type=int, default=100, help="Batch size when chunking exports")
    args = parser.parse_args()

    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

    splitter = RoleSplitter(
        play_text=PlayTextParser().parse(),
        min_silence_ms=args.min_silence_ms,
        silence_thresh=args.silence_thresh,
        verbose=args.verbose,
        chunk_exports=args.chunk_exports,
        chunk_export_size=args.chunk_export_size,
    )
    if args.role:
        roles = [args.role]
    else:
        roles = [p.stem for p in RECORDINGS_DIR.glob("*.wav") if not p.name.startswith("_")]

    for role in roles:
        splitter.process_role(role)


if __name__ == "__main__":
    main()

# Backwards-compatible helper for build.py callers expecting a function.
def process_role(
    role: str,
    *,
    min_silence_ms: int = 1700,
    silence_thresh: int = -45,
    part_filter: str | None = None,
    chunk_size: int = 1,
    verbose: bool = False,
    chunk_exports: bool = False,
    chunk_export_size: int = 100,
) -> None:
    splitter = RoleSplitter(
        play_text=PlayTextParser().parse(),
        min_silence_ms=min_silence_ms,
        silence_thresh=silence_thresh,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
    )
    splitter.process_role(role, part_filter=part_filter)
