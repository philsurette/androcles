#!/usr/bin/env python3
"""Generate WebVTT captions from plan items."""
from __future__ import annotations

from pathlib import Path
from typing import List

from play_plan_builder import PlanItem, SegmentClip, CalloutClip


def fmt_ts(ms: int) -> str:
    hours = ms // 3_600_000
    rem = ms % 3_600_000
    minutes = rem // 60_000
    rem = rem % 60_000
    seconds = rem // 1000
    millis = rem % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def build_captions(plan: List[PlanItem], out_path: Path) -> Path:
    """Write WebVTT captions for all clips with text."""
    lines: List[str] = ["WEBVTT", ""]
    idx = 1
    for item in plan:
        if isinstance(item, (SegmentClip, CalloutClip)):
            text = item.text or ""
            if not text.strip():
                continue
            start_ms = item.offset_ms
            end_ms = item.offset_ms + item.length_ms
            lines.append(str(idx))
            lines.append(f"{fmt_ts(start_ms)} --> {fmt_ts(end_ms)}")
            lines.append(text.strip())
            lines.append("")  # blank separator
            idx += 1
    content = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
    return out_path
