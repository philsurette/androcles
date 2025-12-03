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


import sys
import os
from pathlib import Path
from typing import List
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
    chunk_export_size: int = 25
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

    def split(self, role: str, part_filter: str | None = None) -> float | None:
        src_path = self.splitter.find_recording(role)
        if not src_path:
            print(f"Recording not found for role {role}", file=sys.stderr)
            return None

        #logging.info("Processing role %s from %s", role, src_path)
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

        total_time = self.splitter.last_detect_seconds + self.splitter.last_export_seconds
        if len(spans) != len(expected_ids):
            logging.warning(
                "⚠️  split %3d/%-3d in %4.1fs %s",
                len(spans),
                len(expected_ids),
                total_time,
                os.path.relpath(str(src_path), str(Path.cwd())),
            )
        else:
            logging.info(
                "✅ split %3d/%-3d in %4.1fs %s",
                len(spans),
                len(expected_ids),
                total_time,
                os.path.relpath(str(src_path), str(Path.cwd())),
            )
        return total_time

