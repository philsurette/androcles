#!/usr/bin/env python3
"""
Split role recordings into per-line clips using silence detection.

Expected layout:
- audio/src/<ROLE>.mp3        # raw recording for the role
- playtext/roles/<ROLE>.txt      # role script with block ids and lines

Outputs:
- audio/<ROLE>/<part>_<block>_<line>-<ROLE>.mp3
  with zero-padded ids for easy sorting.

Notes:
- Uses pydub (ffmpeg required) for silence-based splitting.
- Compares produced clip count to expected line count and prints a warning on mismatch.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from pydub import AudioSegment, silence
except ImportError:  # pragma: no cover - dependency notice
    print("Please install pydub (pip install pydub) and ensure ffmpeg is available in PATH.", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
PLAYTEXT_DIR = ROOT / "playtext"
ROLES_DIR = PLAYTEXT_DIR / "roles"
AUDIO_DIR = ROOT / "audio"
SRC_DIR = AUDIO_DIR / "src"


def parse_role(role: str) -> List[Tuple[int, int, int]]:
    """
    Parse the role file to collect expected (part, block, line_index) tuples.
    Line indices are 1-based within each block and count only bullet lines ("  - ").
    """
    path = ROLES_DIR / f"{role}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Role file not found: {path}")

    expected: List[Tuple[int, int, int]] = []
    current_part = None
    current_block = None
    line_idx = 0

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped[0].isdigit():
            # Header line: "part:block ..." optionally with "<"
            head = stripped.split()[0]
            if ":" in head:
                part_str, block_str = head.split(":", 1)
                current_part = int(part_str)
                current_block = int(block_str)
                line_idx = 0
            continue
        if stripped.startswith("- "):
            if current_part is None or current_block is None:
                continue
            line_idx += 1
            expected.append((current_part, current_block, line_idx))
    return expected


def split_audio(source: Path, min_silence_len: int, silence_thresh: int) -> List[AudioSegment]:
    """
    Split an audio file on silence and return list of chunks.
    """
    audio = AudioSegment.from_file(source)
    chunks = silence.split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=200,
    )
    return chunks


def save_chunks(role: str, chunks: List[AudioSegment], expected_ids: List[Tuple[int, int, int]]) -> None:
    """
    Save audio chunks to audio/<ROLE>/ with zero-padded filenames.
    """
    out_dir = AUDIO_DIR / role
    out_dir.mkdir(parents=True, exist_ok=True)

    for path in out_dir.glob("*.mp3"):
        path.unlink()

    pad_part = 1
    pad_block = 4
    pad_line = 2

    for idx, chunk in enumerate(chunks):
        if idx < len(expected_ids):
            part, block, line_idx = expected_ids[idx]
        else:
            part = block = line_idx = 0
        name = f"{str(part).zfill(pad_part)}_{str(block).zfill(pad_block)}_{str(line_idx).zfill(pad_line)}-{role}.mp3"
        chunk.export(out_dir / name, format="mp3")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split role recordings into line-level clips.")
    parser.add_argument("role", help="Role name, e.g., CAPTAIN (expects audio/src/CAPTAIN.mp3 and playtext/roles/CAPTAIN.txt)")
    parser.add_argument("--min-silence-ms", type=int, default=1700, help="Minimum silence length to split on (ms)")
    parser.add_argument("--silence-thresh", type=int, default=-35, help="Silence threshold in dBFS for splitting")
    args = parser.parse_args()

    role = args.role
    source = SRC_DIR / f"{role}.mp3"
    if not source.exists():
        raise FileNotFoundError(f"Source audio not found: {source}")

    expected_ids = parse_role(role)
    chunks = split_audio(source, args.min_silence_ms, args.silence_thresh)
    save_chunks(role, chunks, expected_ids)

    expected_count = len(expected_ids)
    actual_count = len(chunks)
    if expected_count != actual_count:
        print(f"WARNING: expected {expected_count} lines but created {actual_count} clips for role {role}")
    else:
        print(f"OK: created {actual_count} clips for role {role}")


if __name__ == "__main__":
    main()
