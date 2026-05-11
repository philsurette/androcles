#!/usr/bin/env python3
"""Check recorded snippets by role."""
from __future__ import annotations

import csv
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from stager.audiobook.play_plan_builder import PlayPlanBuilder
from stager.shared import paths
from stager.text.play_text_parser import PlayTextParser
from stager.verification.segment_verifier import SegmentVerifier

logger = logging.getLogger(__name__)


def load_timings(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def summarize_rows(rows: List[Dict]) -> List[str]:
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


def summarize(path: Path) -> List[str]:
    return summarize_rows(load_timings(path))


@dataclass
class RecordingChecker:
    paths: paths.PathConfig
    too_short: float = 0.5
    too_long: float = 2.0

    def summarize(self) -> List[str]:
        play = PlayTextParser(paths_config=self.paths).parse()
        builder = PlayPlanBuilder(play=play, paths=self.paths)
        plan = builder.build_audio_plan()
        rows = SegmentVerifier(
            plan=plan,
            too_short=self.too_short,
            too_long=self.too_long,
            play=play,
            paths=self.paths,
        ).compute_rows()
        return summarize_rows(rows)


def main(paths_config: paths.PathConfig | None = None) -> None:
    cfg = paths_config or paths.current()
    for line in RecordingChecker(paths=cfg).summarize():
        logger.info("%s", line)


if __name__ == "__main__":
    main()
