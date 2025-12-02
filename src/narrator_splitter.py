#!/usr/bin/env python3
"""
Split the narrator recording into per-line WAV snippets based on _NARRATOR.blocks.

Naming:
- For entries with a part id: <part>_<block>_<elem>.wav
- For entries without a part id (e.g., pre-heading meta): _<block>_<elem>.wav

Only inline directions are kept from mixed speech blocks; pure description/meta/direction
entries keep all bullet lines.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple
import logging

from audio_splitter import AudioSplitter
from paths import BLOCKS_DIR, BLOCKS_EXT, RECORDINGS_DIR, SEGMENTS_DIR


def parse_narrator_blocks(part_filter: str | None = None) -> List[Tuple[str, str]]:
    """Return ordered (id, text) tuples for narrator lines."""
    path = BLOCKS_DIR / f"_NARRATOR{BLOCKS_EXT}"
    if not path.exists():
        raise FileNotFoundError(f"Narrator blocks not found: {path}")

    expected: List[Tuple[str, str]] = []
    current_part: str | None = None
    current_block: str | None = None
    segments: List[str] = []

    def flush() -> None:
        nonlocal segments, current_part, current_block
        if current_block is None:
            segments = []
            return
        if not segments:
            return
        include_dirs_only = any(seg.startswith("(_") for seg in segments) and any(
            not seg.startswith("(_") for seg in segments
        )
        elem_idx = 0
        for seg in segments:
            elem_idx += 1
            if include_dirs_only and not seg.startswith("(_"):
                continue
            if current_part:
                eid = f"{current_part}_{current_block}_{elem_idx}"
            else:
                eid = f"_{current_block}_{elem_idx}"
            expected.append((eid, seg))
        segments = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped[0].isdigit() or stripped.startswith(":"):
            flush()
            head = stripped.split()[0]
            if ":" in head:
                part, block = head.split(":", 1)
                current_part = part if part else None
                current_block = block
            else:
                current_part = None
                current_block = None
            continue
        if stripped.startswith("-"):
            segments.append(stripped[1:].strip())

    flush()
    return expected


def split_narration(
    part_filter: str | None = None,
    min_silence_ms: int = 1700,
    silence_thresh: int = -45,
    pad_end_ms: int = 200,
    chunk_size: int = 1,
) -> None:
    src_path = RECORDINGS_DIR / "_NARRATOR.wav"
    if not src_path.exists():
        print(f"Narrator recording not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    logging.info("Processing narrator from %s", src_path)
    pf = "" if part_filter == "_" else part_filter
    expected = parse_narrator_blocks(part_filter=pf)
    splitter = AudioSplitter(
        min_silence_ms=min_silence_ms,
        silence_thresh=silence_thresh,
        pad_end_ms=pad_end_ms,
        chunk_size=chunk_size,
    )
    spans = splitter.detect_spans(src_path)
    splitter.export_spans(src_path, spans, [eid for eid, _ in expected], SEGMENTS_DIR / "_NARRATOR")

    if len(spans) != len(expected):
        print(f"WARNING: expected {len(expected)} snippets, got {len(spans)}")
    else:
        print(f"Split narrator into {len(spans)} snippets OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split narrator recording into per-line WAV snippets.")
    parser.add_argument("--min-silence-ms", type=int, default=1700, help="Silence length (ms) to split on (default 1700)")
    parser.add_argument("--silence-thresh", type=int, default=-45, help="Silence threshold dBFS (default -45)")
    parser.add_argument("--pad-end-ms", type=int, default=200, help="Pad each segment end by this many ms (default 200)")
    parser.add_argument("--part", help="Limit to a specific part id, or '_' for no-part entries")
    parser.add_argument("--chunk-size", type=int, default=1, help="Chunk size (ms) for silence detection")
    args = parser.parse_args()
    split_narration(
        part_filter=args.part,
        min_silence_ms=args.min_silence_ms,
        silence_thresh=args.silence_thresh,
        pad_end_ms=args.pad_end_ms,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
