#!/usr/bin/env python3
"""Abstract splitter for roles and narrator recordings."""
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from abc import ABC, abstractmethod

from audio_splitter import AudioSplitter
from play import Play, PlayTextParser
import paths


@dataclass
class SegmentSplitter(ABC):
    play: Play
    role: str
    force: bool = False
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    chunk_size: int = 50
    pad_end_ms: int = 200
    verbose: bool = False
    chunk_exports: bool = False
    chunk_export_size: int = 25
    splitter: AudioSplitter = field(default_factory=AudioSplitter)

    def __post_init__(self) -> None:
        if self.play is None:
            self.play = PlayTextParser().parse()
        # Sync splitter thresholds
        self.splitter.min_silence_ms = self.min_silence_ms
        self.splitter.silence_thresh = self.silence_thresh
        self.splitter.chunk_size = self.chunk_size
        self.splitter.pad_end_ms = self.pad_end_ms
        self.splitter.verbose = self.verbose
        self.splitter.chunk_exports = self.chunk_exports
        self.splitter.chunk_export_size = self.chunk_export_size

    @abstractmethod
    def expected_ids(self, part_filter: str | None = None) -> List[str]:
        """Return expected segment ids for this role."""
        raise NotImplementedError

    def recording_path(self) -> Path:
        """Return the source recording path for the given role."""
        return paths.RECORDINGS_DIR / f"{self.role}.wav"

    def output_dir(self) -> Path:
        """Return the destination directory for split segments."""
        return paths.SEGMENTS_DIR / self.role

    def split(self, part_filter: str | None = None) -> float | None:
        src_path = self.recording_path()
        if not src_path or not src_path.exists():
            print(f"Recording not found for role {self.role}", file=sys.stderr)
            return None

        out_dir = self.output_dir()
        if not self.force and out_dir.exists():
            outputs = list(out_dir.glob("*.wav"))
            if outputs:
                src_mtime = src_path.stat().st_mtime
                oldest_out = min(f.stat().st_mtime for f in outputs)
                if oldest_out > src_mtime:
                    logging.info("⏭️  Skipping split for %s (outputs newer than recording)", self.role)
                    return 0.0

        expected_ids = self.expected_ids(part_filter=part_filter)
        spans = self.splitter.detect_spans(src_path)
        self.splitter.export_spans(
            src_path,
            spans,
            expected_ids,
            out_dir,
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
