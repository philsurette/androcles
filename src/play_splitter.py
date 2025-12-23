#!/usr/bin/env python3
"""Facade for splitting all role and narrator recordings."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from play import Play
from play_text_parser import PlayTextParser
import paths
from role_splitter import RoleSplitter, CalloutSplitter
from narrator_splitter import NarratorSplitter
from announcer_splitter import AnnouncerSplitter
from announcer import Announcer, LibrivoxAnnouncer


@dataclass
class PlaySplitter:
    play: Play
    force: bool = False
    min_silence_ms: int = 1700
    silence_thresh: int = -45
    pad_end_ms: int = 200
    chunk_size: int = 50
    verbose: bool = False
    chunk_exports: bool = True
    chunk_export_size: int = 25

    def __post_init__(self) -> None:
        if self.play is None:
            self.play = PlayTextParser().parse()


    def split_roles(self, role_filter: Optional[str] = None, part_filter: Optional[str] = None) -> float:
        total = 0.0
        for role_name in [r.name for r in self.play.getRoles()]:
            if role_filter and role_filter != role_name:
                continue
            splitter = RoleSplitter(
                play=self.play,
                role=role_name,
                force=self.force,
                min_silence_ms=self.min_silence_ms,
                silence_thresh=self.silence_thresh,
                chunk_size=self.chunk_size,
                pad_end_ms=self.pad_end_ms,
                verbose=self.verbose,
                chunk_exports=self.chunk_exports,
                chunk_export_size=self.chunk_export_size,
            )
            elapsed = splitter.split(part_filter=part_filter)
            if elapsed:
                total += elapsed
        return total

    def split_callouts(self) -> float:
        splitter = CalloutSplitter(
            play=self.play,
            role="_CALLER",
            force=self.force,
            min_silence_ms=self.min_silence_ms,
            silence_thresh=self.silence_thresh,
            chunk_size=self.chunk_size,
            pad_end_ms=self.pad_end_ms,
            verbose=self.verbose,
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )
        elapsed = splitter.split(part_filter=None)
        return elapsed or 0.0

    def split_announcer(self) -> float:
        splitter = AnnouncerSplitter(
            play=self.play,
            force=self.force,
            min_silence_ms=self.min_silence_ms,
            silence_thresh=self.silence_thresh,
            chunk_size=self.chunk_size,
            pad_end_ms=self.pad_end_ms,
            verbose=self.verbose,
            chunk_exports=self.chunk_exports,
            chunk_export_size=self.chunk_export_size,
        )
        elapsed = splitter.split(part_filter=None)
        return elapsed or 0.0
        
    def split_narrator(self, part_filter: Optional[str] = None) -> float:
        splitter = NarratorSplitter(
            play=self.play,
            force=self.force,
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
        callout_time = 0.0
        announcer_time = 0.0
        if role_filter is None:
            roles_time = self.split_roles(role_filter=None, part_filter=part_filter)
            narr_time = self.split_narrator(part_filter=part_filter)
            # Always split callouts from _CALLER.wav when doing a full split.
            callout_time = self.split_callouts()
            announcer_time = self.split_announcer()
        elif role_filter == "_NARRATOR":
            narr_time = self.split_narrator(part_filter=part_filter)
        elif role_filter == "_CALLER":
            callout_time = self.split_callouts()
        elif role_filter == "_ANNOUNCER":
            announcer_time = self.split_announcer()
        else:
            roles_time = self.split_roles(role_filter=role_filter, part_filter=part_filter)

        logging.info(
            "✅  Segments split completed in %.0fs (roles %.3fs, narrator %.3fs, callouts %.3fs, announcer %.3fs)",
            roles_time + narr_time + callout_time + announcer_time,
            roles_time,
            narr_time,
            callout_time,
            announcer_time,
        )
        return roles_time, narr_time
