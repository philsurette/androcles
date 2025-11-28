#!/usr/bin/env python3
"""
Sanity-check split role audio snippets against expected blocks.

For each role:
- Verify every expected speech line has a corresponding WAV snippet in build/audio/<role>/.
- Estimate expected duration from the text and warn if the actual WAV duration is
  outside 50%–200% of that estimate.
- Warn about unexpected extra files.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from pydub import AudioSegment

from paths import BLOCKS_DIR, BLOCKS_EXT, SEGMENTS_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_expected(role: str) -> List[Tuple[str, str]]:
    """
    Return ordered (id, text) tuples for speech lines in the role's blocks file.
    An id is formatted as part_block_elem with underscores.
    """
    path = BLOCKS_DIR / f"{role}{BLOCKS_EXT}"
    if not path.exists():
        raise FileNotFoundError(f"Blocks file not found for role {role}: {path}")

    expected: List[Tuple[str, str]] = []
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
                continue  # direction; not expected in role audio
            expected.append((f"{current_part}_{current_block}_{elem_idx}", body))

    return expected


def expected_duration_seconds(text: str, wpm: int = 150, pad: float = 0.2) -> float:
    """Estimate speech duration in seconds based on word count and padding."""
    words = [w for w in text.split() if w]
    words_per_sec = wpm / 60.0
    base = len(words) / words_per_sec if words else 0.3
    return base + pad


def check_role(role: str, tolerance_low: float, tolerance_high: float) -> None:
    out_dir = SEGMENTS_DIR / role
    if not out_dir.exists():
        logging.warning("No audio output dir for role %s: %s", role, out_dir)
        return

    expected = load_expected(role)
    expected_map: Dict[str, str] = {eid: text for eid, text in expected}

    for eid, text in expected:
        fpath = out_dir / f"{eid}.wav"
        if not fpath.exists():
            logging.error("%s missing snippet %s", role, eid)
            continue
        audio = AudioSegment.from_file(fpath)
        actual = len(audio) / 1000.0
        expected_sec = expected_duration_seconds(text)
        if not (tolerance_low * expected_sec <= actual <= tolerance_high * expected_sec):
            logging.warning(
                "%s %s duration off: actual %.2fs vs expected %.2fs (text=%s)",
                role,
                eid,
                actual,
                expected_sec,
                text,
            )

    # Report extras
    for f in out_dir.glob("*.wav"):
        stem = f.stem
        if stem not in expected_map:
            logging.warning("%s unexpected file: %s", role, f.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check split role WAV files against expected blocks.")
    parser.add_argument("--role", help="Role to check (default: all roles with audio in build/audio)")
    parser.add_argument(
        "--tolerance",
        type=float,
        nargs=2,
        metavar=("LOW", "HIGH"),
        default=(0.5, 2.0),
        help="Allowed ratio range of actual/expected duration (default 0.5 2.0)",
    )
    args = parser.parse_args()

    roles = [args.role] if args.role else [p.name for p in AUDIO_OUT_DIR.iterdir() if p.is_dir()]
    for role in roles:
        check_role(role, args.tolerance[0], args.tolerance[1])


if __name__ == "__main__":
    main()
