#!/usr/bin/env python3
import sys
from pathlib import Path
import csv
import re

def count_words(text: str) -> int:
    # Split on any sequence of letters/numbers/apostrophes
    words = re.findall(r"[A-Za-z0-9']+", text)
    return len(words)

def main():
    if len(sys.argv) < 2:
        print("Usage: wordcount.py CHAR_DIR [output.csv]")
        sys.exit(1)

    indir = Path(sys.argv[1])
    outfile = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("wordcount.csv")

    if not indir.is_dir():
        print(f"Error: {indir} is not a directory containing character .txt files.")
        sys.exit(1)

    counts = []

    for txt in indir.glob("*.txt"):
        speaker = txt.stem
        text = txt.read_text(encoding="utf-8")
        wc = count_words(text)
        counts.append((speaker, wc))

    if not counts:
        print("No .txt files found.")
        sys.exit(1)

    # Total words across all characters
    total_words = sum(wc for _, wc in counts)

    # Sort by word count descending
    counts.sort(key=lambda x: x[1], reverse=True)

    # Add percentages
    rows = []
    for speaker, wc in counts:
        pct = (wc / total_words * 100) if total_words else 0.0
        rows.append((speaker, wc, f"{pct:.1f}"))

    # Write CSV
    with outfile.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Character", "WordCount", "Percent"])
        writer.writerows(rows)
        writer.writerow(["Total", total_words, "100.0"])

    print(f"Wrote {outfile} with {len(counts)} characters + total row.")

if __name__ == "__main__":
    main()
