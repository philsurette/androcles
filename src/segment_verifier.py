#!/usr/bin/env python3
"""Verify split audio segments."""
from __future__ import annotations

import logging
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from pydub import AudioSegment

from narrator_splitter import parse_narrator_blocks
from role_split_checker import load_expected as load_role_expected, expected_duration_seconds
from paths import RECORDINGS_DIR, SEGMENTS_DIR, AUDIO_OUT_DIR
from play_plan_builder import PlayPlanBuilder
from play_text import PlayTextParser
import re

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_id(eid: str):
    """
    Parse ids like '1_80_2' or '_7_1' into ints (part, block, seg).
    No part -> part is None.
    """
    parts = eid.split("_")
    if len(parts) == 3:
        part = int(parts[0]) if parts[0] else None
        block = int(parts[1])
        seg = int(parts[2])
    elif len(parts) == 2:
        part = None
        block = int(parts[0])
        seg = int(parts[1])
    else:
        part = block = seg = None
    return part, block, seg


@dataclass
class SegmentVerifier:
    plan: List
    tol_low: float = 0.5
    tol_high: float = 2.0
    _plan_start_map: Dict[str, float] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._build_plan_start_map()

    def gather_expected(self) -> List[Dict]:
        rows: List[Dict] = []
        # Roles
        for role in [p.stem for p in RECORDINGS_DIR.glob("*.wav") if not p.name.startswith("_") and p.stem != "offsets"]:
            for eid, text in load_role_expected(role):
                rows.append({"id": eid, "role": role, "text": text})
        # Narrator
        for eid, text in parse_narrator_blocks():
            rows.append({"id": eid, "role": "", "text": text})
        return rows

    def verify_segments(self) -> List[Dict]:
        """Compute timing verification rows."""
        rows = self.compute_rows()
        logging.info("Computed %d timing rows", len(rows))
        return rows

    def compute_rows(self) -> List[Dict]:
        rows = self.gather_expected()
        punct = set(string.punctuation)
        for row in rows:
            role = row["role"] or "_NARRATOR"
            fpath = SEGMENTS_DIR / role / f"{row['id']}.wav"
            row["expected_seconds"] = None
            row["actual_seconds"] = None
            row["percent"] = None
            row["warning"] = ""
            row["start"] = None

            text = row["text"]
            if text and not all(ch in punct for ch in text):
                row["expected_seconds"] = expected_duration_seconds(text)

            if fpath.exists():
                audio = AudioSegment.from_file(fpath)
                row["actual_seconds"] = round(len(audio) / 1000.0, 1)
                start_sec = self._plan_start_map.get(row["id"])
                if start_sec is not None:
                    mins = int(start_sec // 60)
                    secs = start_sec - mins * 60
                    row["start"] = f"{mins}:{secs:04.1f}"
            else:
                logging.error("Missing snippet %s for role %s", row["id"], row["role"])
                row["warning"] = "-"
                continue

            if row["expected_seconds"]:
                exp = round(row["expected_seconds"], 1) if row["expected_seconds"] is not None else None
                row["expected_seconds"] = exp
                act = row["actual_seconds"]
                if exp:
                    row["percent"] = round((act / exp) * 100.0, 1)
                    # Apply thresholds; skip warnings if actual is very short.
                    if act >= 2.0:
                        if act < self.tol_low * exp and exp >= 1.0:
                            row["warning"] = "<"
                        elif act > self.tol_high * exp:
                            row["warning"] = ">"
                    if row["warning"]:
                        logging.warning(
                            "%s %s duration off: actual %.2fs vs expected %.2fs",
                            role,
                            row["id"],
                            act,
                            exp,
                        )

        def sort_key(row: Dict):
            pid, bid, sid = parse_id(row["id"])
            part = pid if pid is not None else -1
            block = bid if bid is not None else -1
            seg = sid if sid is not None else -1
            return (part, block, seg)

        rows.sort(key=sort_key)
        return rows

    def _build_plan_start_map(self) -> None:
        """Build a mapping clip_id -> start seconds using the provided plan."""
        for item in self.plan:
            if not hasattr(item, "clip_id") or not getattr(item, "clip_id"):
                continue
            clip_id = str(getattr(item, "clip_id"))
            # Clip ids in plans use ':' separators; convert to '_' to match segment filenames/ids.
            norm_id = clip_id.replace(":", "_")
            self._plan_start_map[norm_id] = round(getattr(item, "offset_ms", 0) / 1000.0, 1)


if __name__ == "__main__":
    play = PlayTextParser().parse()
    builder = PlayPlanBuilder(play_text=play)
    plan, _ = builder.build_audio_plan(parts=builder.list_parts())
    SegmentVerifier(plan=plan).verify_segments()
