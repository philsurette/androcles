#!/usr/bin/env python3
"""
Check narrator snippets against expected _NARRATOR.blocks content.

Verifies presence and approximate duration (default 50%–200% of estimate).
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Tuple

from pydub import AudioSegment

from narrator_splitter import parse_narrator_blocks
from paths import AUDIO_OUT_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def expected_duration_seconds(text: str, wpm: int = 150, pad: float = 0.2) -> float:
    words = [w for w in text.split() if w]
    words_per_sec = wpm / 60.0
    base = len(words) / words_per_sec if words else 0.3
    return base + pad


def check_narrator(tolerance_low: float, tolerance_high: float) -> None:
    out_dir = AUDIO_OUT_DIR / "_NARRATOR"
    if not out_dir.exists():
        logging.error("Narrator output dir not found: %s", out_dir)
        return

    expected = parse_narrator_blocks()
    expected_ids = {eid for eid, _ in expected}
    text_map = {eid: text for eid, text in expected}

    for eid, text in expected:
        fpath = out_dir / f"{eid}.wav"
        if not fpath.exists():
            logging.error("Missing narrator snippet %s", eid)
            continue
        audio = AudioSegment.from_file(fpath)
        actual = len(audio) / 1000.0
        exp = expected_duration_seconds(text)
        if not (tolerance_low * exp <= actual <= tolerance_high * exp):
            logging.warning(
                "Narrator %s duration off: actual %.2fs vs expected %.2fs (text=%s)",
                eid,
                actual,
                exp,
                text,
            )

    for f in out_dir.glob("*.wav"):
        if f.stem not in expected_ids:
            logging.warning("Unexpected narrator file: %s", f.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check narrator split WAV files against _NARRATOR.blocks.")
    parser.add_argument(
        "--tolerance",
        type=float,
        nargs=2,
        metavar=("LOW", "HIGH"),
        default=(0.5, 2.0),
        help="Allowed ratio range of actual/expected duration (default 0.5 2.0)",
    )
    args = parser.parse_args()
    check_narrator(args.tolerance[0], args.tolerance[1])


if __name__ == "__main__":
    main()
