#!/usr/bin/env python3
"""Split announcer recording into per-key WAVs based on _ANNOUNCER.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from stager.audio.segment_splitter import SegmentSplitter
from stager.text.announcer import Announcer, select_announcer


@dataclass
class AnnouncerSplitter(SegmentSplitter):
    announcer: Announcer = None
    build_type: str = "custom"
    role: str = "_ANNOUNCER"

    def extra_outputs(self):
        if not self.play.reading_metadata.dramatic_reading:
            return []
        readers_dir = self.paths.build_dir / "audio" / "readers"
        return list(readers_dir.glob(f"{self.role}*.wav")) if readers_dir.exists() else []

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.announcer is None:
            self.announcer = select_announcer(self.play, build_type=self.build_type)

    def expected_ids(self, part_filter: str | None = None) -> list[str]:
        return [a.key_as_filename() for a in self.announcer.announcements()]

    def pre_export_spans(self, spans, expected_ids, source_path: Path):
        if not spans:
            logging.warning("Expected announcer spans but found none")
            return spans
        if not self.play.reading_metadata.dramatic_reading:
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
