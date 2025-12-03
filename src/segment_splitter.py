#!/usr/bin/env python3
"""Facade for splitting all role and narrator recordings."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from play_text import PlayText, PlayTextParser
from paths import RECORDINGS_DIR
from role_splitter import RoleSplitter
from narrator_splitter import NarratorSplitter


@dataclass
class SegmentSplitter:
    play_text: PlayText
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    pad_end_ms: int = 200
    chunk_size: int = 50
    verbose: bool = False
    chunk_exports: bool = True
    chunk_export_size: int = 25

    def __post_init__(self) -> None:
        if self.play_text is None:
            self.play_text = PlayTextParser().parse()

    def split_roles(self, role_filter: Optional[str] = None, part_filter: Optional[str] = None) -> float:
        splitter = RoleSplitter(
            play_text=self.play_text,
            min_silence_ms=self.min_silence_ms,
            silence_thresh=self.silence_thresh,
            chunk_size=self.chunk_size,
            pad_end_ms=self.pad_end_ms,
            verbose=self.verbose,
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )
        total = 0.0
        for rec in RECORDINGS_DIR.glob("*.wav"):
            if rec.name.startswith("_"):
                continue
            role = rec.stem
            if role_filter and role_filter != role:
                continue
            elapsed = splitter.process_role(role, part_filter=part_filter)
            if elapsed:
                total += elapsed
        return total

    def split_narrator(self, part_filter: Optional[str] = None) -> float:
        splitter = NarratorSplitter(
            play_text=self.play_text,
            min_silence_ms=self.min_silence_ms,
            silence_thresh=self.silence_thresh,
            pad_end_ms=self.pad_end_ms,
            chunk_size=self.chunk_size,
            verbose=self.verbose,
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )
        elapsed = splitter.split(part_filter=part_filter)
        return elapsed or 0.0

    def split_all(self, part_filter: Optional[str] = None, role_filter: Optional[str] = None) -> tuple[float, float]:
        roles_time = 0.0
        narr_time = 0.0
        if role_filter is None:
            roles_time = self.split_roles(role_filter=None, part_filter=part_filter)
            narr_time = self.split_narrator(part_filter=part_filter)
        elif role_filter == "_NARRATOR":
            narr_time = self.split_narrator(part_filter=part_filter)
        else:
            roles_time = self.split_roles(role_filter=role_filter, part_filter=part_filter)

        logging.info(
            "✅  Segments split completed in %.0fs (roles %.3fs, narrator %.3fs)",
            roles_time + narr_time,
            roles_time,
            narr_time,
        )
        return roles_time, narr_time
