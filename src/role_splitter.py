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

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging

from audio_splitter import detect_spans_ms, export_spans_ffmpeg, find_recording
from paths import BLOCKS_DIR, BLOCKS_EXT, AUDIO_OUT_DIR, RECORDINGS_DIR


def load_expected(role: str, part_filter: str | None = None) -> List[str]:
    """Return ordered ids (part_block_elem) for speech lines in the role's blocks file."""
    path = BLOCKS_DIR / f"{role}{BLOCKS_EXT}"
    if not path.exists():
        raise FileNotFoundError(f"Blocks file not found for role {role}: {path}")

    expected: List[str] = []
    current_part = None
    current_block = None
    elem_idx = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0].isdigit() or stripped.startswith(":"):
            head = stripped.split()[0]
            if ":" in head:
                part, block = head.split(":", 1)
                current_part, current_block = part, block
                elem_idx = 0
            continue

        if stripped.startswith("-"):
            elem_idx += 1
            body = stripped[1:].strip()
            if body.startswith("(_"):
                continue  # direction; count it but don't expect audio
            if part_filter is None or part_filter == current_part:
                expected.append(f"{current_part}_{current_block}_{elem_idx}")

    return expected


def process_role(
    role: str, min_silence_ms: int, silence_thresh: int, part_filter: str | None = None, chunk_size: int = 1
) -> None:
    src_path = find_recording(role)
    if not src_path:
        print(f"Recording not found for role {role}", file=sys.stderr)
        return

    logging.info("Processing role %s from %s", role, src_path)
    expected_ids = load_expected(role, part_filter=part_filter)
    spans = detect_spans_ms(src_path, min_silence_ms, silence_thresh, pad_end_ms=200, chunk_size=chunk_size)
    export_spans_ffmpeg(src_path, spans, expected_ids, AUDIO_OUT_DIR / role)

    if len(spans) != len(expected_ids):
        print(f"WARNING {role}: expected {len(expected_ids)} snippets, got {len(spans)}")
    else:
        print(f"{role}: split {len(spans)} snippets OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split role recordings into per-line mp3 snippets.")
    parser.add_argument(
        "--role",
        help="Role name to process (default: all recordings in plays/.../recordings excluding leading underscore).",
    )
    parser.add_argument("--min-silence-ms", type=int, default=1700, help="Silence length (ms) to split on (default 1700)")
    parser.add_argument("--silence-thresh", type=int, default=-35, help="Silence threshold dBFS (default -35)")
    args = parser.parse_args()

    AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.role:
        roles = [args.role]
    else:
        roles = [p.stem for p in RECORDINGS_DIR.glob("*.wav") if not p.name.startswith("_")]

    for role in roles:
        process_role(role, args.min_silence_ms, args.silence_thresh)


if __name__ == "__main__":
    main()
