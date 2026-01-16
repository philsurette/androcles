#!/usr/bin/env python3
"""Split announcer recording into per-key WAVs based on _ANNOUNCER.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from segment_splitter import SegmentSplitter
from announcer import Announcer, LibrivoxAnnouncer
import paths


@dataclass
class AnnouncerSplitter(SegmentSplitter):
    announcer: Announcer = None
    role: str = "_ANNOUNCER"

    def extra_outputs(self):
        readers_dir = self.paths.build_dir / "audio" / "readers"
        return list(readers_dir.glob(f"{self.role}*.wav")) if readers_dir.exists() else []

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.announcer is None:
            self.announcer = LibrivoxAnnouncer(self.play) 

    def expected_ids(self, part_filter: str | None = None) -> list[str]:
        return [a.key_as_filename() for a in self.announcer.announcements()]

    def pre_export_spans(self, spans, expected_ids, source_path: Path):
        if not spans:
            logging.warning("Expected announcer intro but found no spans to split")
            return spans
        # First span is the reader intro
        readers_dir = self.paths.build_dir / "audio" / "readers"
        readers_dir.mkdir(parents=True, exist_ok=True)
        self.splitter.export_spans(
            source_path,
            [spans[0]],
            [self.role],
            readers_dir,
            chunk_exports=False,
            cleanup_existing=False,
        )
        return spans[1:]

    def output_dir(self) -> Path:
        return self.paths.segments_dir / self.role
