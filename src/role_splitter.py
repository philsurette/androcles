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
from typing import List
import logging
from dataclasses import dataclass
from play import RoleBlock, SpeechSegment, SimultaneousSegment
from segment_splitter import SegmentSplitter
import paths


@dataclass
class RoleSplitter(SegmentSplitter):

    def expected_ids(self, part_filter: str | None = None) -> List[str]:
        """
        Return expected segment ids for speech lines of a role, optionally filtered by part.
        Uses in-memory PlayText blocks (directions counted for numbering, only speech for the role emits ids).
        """
        ids: List[str] = []
        role_obj = self.play.getRole(self.role)

        blocks: List[RoleBlock] = role_obj.get_blocks(int(part_filter) if part_filter is not None else None)
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
                if isinstance(seg, SpeechSegment) and seg.role == self.role:
                    ids.append(str(seg.segment_id))
                elif isinstance(seg, SimultaneousSegment) and self.role in getattr(seg, "roles", []):
                    ids.append(str(seg.segment_id))
        return ids


@dataclass
class CalloutSplitter(SegmentSplitter):
    """
    Split the callout recording into per-callout wavs.

    Input: plays/.../recordings/_CALLER.wav and build/markdown/roles/_CALLER.md
    Output: build/audio/callouts/<CALLOUT>.wav (one per callout name)
    """

    def expected_ids(self, part_filter: str | None = None) -> List[str]:
        """Callout ids are the callout names listed in _CALLER.md."""
        path = paths.MARKDOWN_ROLES_DIR / "_CALLER.md"
        if not path.exists():
            raise RuntimeError(f"Missing callout script: {path}")
        ids: List[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or not line.startswith("-"):
                continue
            name = line.lstrip("-").strip()
            if name:
                ids.append(name)
        return ids

    def output_dir(self) -> Path:
        return paths.BUILD_DIR / "audio" / "callouts"

    def source_path(self) -> Path:
        return paths.RECORDINGS_DIR / "_CALLER.wav"
