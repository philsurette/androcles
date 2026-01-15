#!/usr/bin/env python3
"""Abstract splitter for roles and narrator recordings."""
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from abc import ABC, abstractmethod

from audio_splitter import AudioSplitter
from play import Play
from play_text_parser import PlayTextParser
import paths


@dataclass
class SegmentSplitter(ABC):
    play: Play
    role: str
    paths: paths.PathConfig = field(default_factory=paths.current)
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
            self.play = PlayTextParser(paths_config=self.paths).parse()
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
        return self.paths.recordings_dir / f"{self.role}.wav"

    def pre_export_spans(self, spans: List[tuple[int, int]], expected_ids: List[str], source_path: Path) -> List[tuple[int, int]]:
        """
        Hook for subclasses to adjust spans or emit extra exports before main export.
        Default implementation is a no-op.
        """
        return spans

    def output_dir(self) -> Path:
        """Return the destination directory for split segments."""
        return self.paths.segments_dir / self.role

    def split(self, part_filter: str | None = None) -> float | None:
        src_path = self.recording_path()
        if not src_path or not src_path.exists():
            logging.error(f"Recording not found for role {self.role}", file=sys.stderr)
            return None

        out_dir = self.output_dir()
        outputs = list(out_dir.glob("*.wav")) if out_dir.exists() else []

        src_mtime = src_path.stat().st_mtime
        aup3 = src_path.with_suffix(".aup3")
        aup3_mtime = aup3.stat().st_mtime if aup3.exists() else None
        reference_mtime = max(src_mtime, aup3_mtime or src_mtime)

        if aup3_mtime and outputs:
            newest_out_ns = max(f.stat().st_mtime_ns for f in outputs)
            aup3_ns = aup3.stat().st_mtime_ns
            if newest_out_ns < aup3_ns:
                def fmt(ts_ns: int) -> str:
                    return datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).isoformat()
                logging.warning(
                    "⚠️  %s is newer than existing exports for %s (aup3 %s vs newest export %s); consider re-exporting",
                    aup3.name,
                    self.role,
                    fmt(aup3_ns),
                    fmt(newest_out_ns),
                )

        if not self.force and outputs:
            oldest_out = min(f.stat().st_mtime for f in outputs)
            if oldest_out > reference_mtime:
                logging.info("⏭️  Skipping split for %s (outputs newer than recording/project)", self.role)
                return 0.0

        expected_ids = self.expected_ids(part_filter=part_filter)
        spans = self.splitter.detect_spans(src_path)
        spans = self.pre_export_spans(spans, expected_ids, src_path)
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
