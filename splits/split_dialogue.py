#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from collections import defaultdict

HEADER_RE = re.compile(r"^\s*([A-Z][A-Z0-9' \-]*)\.\s*$")

def split_dialogue(text: str):
    lines = text.splitlines()

    current_speaker = None
    current_block = []
    blocks_by_speaker = defaultdict(list)

    def flush_block():
        nonlocal current_block
        if current_speaker and current_block:
            # join lines into one, collapse extra whitespace
            joined = " ".join(current_block)
            joined = re.sub(r"\s+", " ", joined).strip()
            if joined:
                blocks_by_speaker[current_speaker].append(joined)
        current_block = []

    for line in lines:
        header_match = HEADER_RE.match(line)
        if header_match:
            flush_block()
            current_speaker = header_match.group(1).strip()
            continue

        if not line.strip():  # blank line ends a block
            flush_block()
            continue

        if current_speaker:
            current_block.append(line.strip())

    flush_block()
    return blocks_by_speaker


def write_blocks(blocks_by_speaker, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    for speaker, blocks in blocks_by_speaker.items():
        outfile = outdir / f"{speaker}.txt"
        with outfile.open("w", encoding="utf-8") as f:
            for b in blocks:
                f.write(b + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: split_play.py INPUT.txt [OUTDIR]")
        sys.exit(1)

    infile = Path(sys.argv[1])
    outdir = Path(sys.argv[2]) if len(sys.argv) >= 3 else infile.parent / "chars"

    text = infile.read_text(encoding="utf-8")
    blocks_by_speaker = split_dialogue(text)
    write_blocks(blocks_by_speaker, outdir)

    print(f"Wrote {len(blocks_by_speaker)} character files to {outdir}")


if __name__ == "__main__":
    main()
