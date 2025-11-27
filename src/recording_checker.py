#!/usr/bin/env python3
"""Check recorded snippets by role using timings.csv."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from paths import AUDIO_OUT_DIR


def load_timings(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def summarize(path: Path) -> List[str]:
    rows = load_timings(path)
    per_role: Dict[str, List[Dict]] = defaultdict(list)
    for row in rows:
        role = row.get("role", "") or "_NARRATOR"
        per_role[role].append(row)

    summary_lines: List[str] = []
    for role in sorted(per_role):
        warnings = [r for r in per_role[role] if r.get("warning")]
        missing = [r for r in warnings if r.get("warning") == "-"]
        if missing:
            symbol = "✖"
        elif warnings:
            symbol = "!"
        else:
            symbol = "✓"
        ids = [r["id"] for r in warnings]
        if ids:
            summary_lines.append(f"{symbol} {role}: {' '.join(ids)}")
        else:
            summary_lines.append(f"{symbol} {role}: OK")
    return summary_lines


def main() -> None:
    timings_path = AUDIO_OUT_DIR / "timings.csv"
    if not timings_path.exists():
        print(f"timings.csv not found at {timings_path}")
        return
    for line in summarize(timings_path):
        print(line)


if __name__ == "__main__":
    main()
