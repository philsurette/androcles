#!/usr/bin/env python3
"""Verify split audio segments."""
from __future__ import annotations

import logging
import string
from pathlib import Path
from typing import List, Dict

from pydub import AudioSegment

from narrator_splitter import parse_narrator_blocks
from role_split_checker import load_expected as load_role_expected, expected_duration_seconds
from paths import RECORDINGS_DIR, SEGMENTS_DIR, AUDIO_OUT_DIR
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


def gather_expected() -> List[Dict]:
    rows: List[Dict] = []
    # Roles
    for role in [p.stem for p in RECORDINGS_DIR.glob("*.wav") if not p.name.startswith("_") and p.stem != "offsets"]:
        for eid, text in load_role_expected(role):
            rows.append({"id": eid, "role": role, "text": text})
    # Narrator
    for eid, text in parse_narrator_blocks():
        rows.append({"id": eid, "role": "", "text": text})
    return rows


def verify_segments(tol_low: float = 0.5, tol_high: float = 2.0) -> List[Dict]:
    """Compute timing verification rows."""
    rows = compute_rows(tol_low, tol_high)
    logging.info("Computed %d timing rows", len(rows))
    return rows


def compute_rows(tol_low: float = 0.5, tol_high: float = 2.0) -> List[Dict]:
    rows = gather_expected()
    punct = set(string.punctuation)
    offsets_cache: Dict[str, Dict[str, float]] = {}

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
            if role not in offsets_cache:
                offsets_cache[role] = load_offsets(role)
            start_sec = offsets_cache[role].get(row["id"])
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
                    if act < tol_low * exp and exp >= 1.0:
                        row["warning"] = "<"
                    elif act > tol_high * exp:
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


def load_offsets(role: str) -> Dict[str, float]:
    offsets_path = SEGMENTS_DIR / role / "offsets.txt"
    mapping: Dict[str, float] = {}
    if not offsets_path.exists():
        return mapping
    for line in offsets_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        eid, stamp = parts
        if ":" in stamp:
            mins, secs = stamp.split(":")
            try:
                total = int(mins) * 60 + float(secs)
                mapping[eid] = round(total, 1)
            except ValueError:
                continue
    return mapping


if __name__ == "__main__":
    verify_segments()
