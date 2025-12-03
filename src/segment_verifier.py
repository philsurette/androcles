#!/usr/bin/env python3
"""Verify split audio segments."""
from __future__ import annotations

import logging
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from pydub import AudioSegment

from paths import RECORDINGS_DIR, SEGMENTS_DIR, AUDIO_OUT_DIR
from play_plan_builder import PlayPlanBuilder
from play_text import PlayTextParser, PlayText
from segment import  MetaSegment, DescriptionSegment, DirectionSegment, SpeechSegment
from block import RoleBlock, MetaBlock, DescriptionBlock, DirectionBlock

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def expected_duration_seconds(text: str, wpm: int = 150, pad: float = 0.2) -> float:
    """Estimate speech duration in seconds based on word count and padding."""
    words = [w for w in text.split() if w]
    words_per_sec = wpm / 60.0
    base = len(words) / words_per_sec if words else 0.3
    return base + pad

def parse_id(eid: str):
    """
    Parse ids like '1_80_2' or '_7_1' into ints (part, block, seg).
    No part -> part is None.
    """
    parts = eid.split("_")
    if len(parts) == 3:
        part = int(parts[0]) if parts[0] else None
        block = int(parts[1])
        seg = int(parts[2])
    elif len(parts) == 2:
        part = None
        block = int(parts[0])
        seg = int(parts[1])
    else:
        part = block = seg = None
    return part, block, seg


@dataclass
class SegmentVerifier:
    plan: List
    too_short: float = 0.5
    too_long: float = 2.0
    play_text: PlayText | None = None
    _plan_start_map: Dict[str, float] = field(init=False, default_factory=dict)
    _offsets_map: Dict[str, Dict[str, str]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.play_text is None:
            self.play_text = PlayTextParser().parse()
        self._build_plan_start_map()
        self._load_offsets()

    def gather_expected(self) -> List[Dict]:
        rows: List[Dict] = []
        if self.play_text is None:
            return rows
        # Narrator/meta content
        rows.extend(self._gather_narrator_segments())

        # Roles (skip narrator to avoid double counting)
        for role_obj in self.play_text.getRoles():
            role = role_obj.name
            if role == "_NARRATOR":
                continue
            for blk in role_obj.blocks:
                # Skip block if part filter logic is needed; here we include all.
                seq = 0
                for seg in blk.segments:
                    text = getattr(seg, "text", "").strip()
                    if not text or text in {".", ",", ":", ";"}:
                        continue
                    seq += 1
                    if isinstance(seg, SpeechSegment) and seg.role == role:
                        rows.append(
                            {
                                "id": f"{'' if blk.block_id.part_id is None else blk.block_id.part_id}_{blk.block_id.block_no}_{seq}",
                                "role": role,
                                "text": text,
                            }
                        )
        return rows

    def _gather_narrator_segments(self) -> List[Dict]:
        """Collect narrator/meta segments directly from PlayText."""
        rows: List[Dict] = []
        if self.play_text is None:
            return rows

        for blk in self.play_text:
            if isinstance(blk, (MetaBlock, DescriptionBlock, DirectionBlock)):
                relevant = blk.segments
            elif isinstance(blk, RoleBlock):
                relevant = []
                for seg in blk.segments:
                    if isinstance(seg, SpeechSegment) and getattr(seg, "role", "") == "_NARRATOR":
                        relevant.append(seg)
                    elif isinstance(seg, DirectionSegment):
                        relevant.append(seg)
            else:
                continue

            for seg in relevant:
                text = getattr(seg, "text", "").strip()
                if not text or text in {".", ",", ":", ";"}:
                    continue
                if isinstance(seg, (MetaSegment, DescriptionSegment, DirectionSegment)) or (
                    isinstance(seg, SpeechSegment) and getattr(seg, "role", "") == "_NARRATOR"
                ):
                    rows.append(
                        {
                            "id": f"{'' if blk.block_id.part_id is None else blk.block_id.part_id}_{blk.block_id.block_no}_{seg.segment_id.segment_no}",
                            "role": "",
                            "text": text,
                        }
                    )
        return rows

    def verify_segments(self) -> List[Dict]:
        """Compute timing verification rows."""
        rows = self.compute_rows()
        logging.info("Computed %d timing rows", len(rows))
        return rows

    def compute_rows(self) -> List[Dict]:
        rows = self.gather_expected()
        punct = set(string.punctuation)
        for row in rows:
            role = row["role"] or "_NARRATOR"
            fpath = SEGMENTS_DIR / role / f"{row['id']}.wav"
            row["expected_seconds"] = None
            row["actual_seconds"] = None
            row["percent"] = None
            row["warning"] = ""
            row["start"] = None
            row["src_offset"] = ""

            text = row["text"]
            if text and not all(ch in punct for ch in text):
                row["expected_seconds"] = expected_duration_seconds(text)

            if fpath.exists():
                audio = AudioSegment.from_file(fpath)
                row["actual_seconds"] = round(len(audio) / 1000.0, 1)
                start_sec = self._plan_start_map.get(row["id"])
                if start_sec is not None:
                    row["start"] = self._format_seconds(start_sec)
                role_key = row["role"] or "_NARRATOR"
                src_offset = self._offsets_map.get(role_key, {}).get(row["id"])
                if src_offset:
                    row["src_offset"] = self._format_seconds(self._parse_timecode(src_offset))
            else:
                logging.error("Missing snippet %s for role %s", row["id"], row["role"])
                row["warning"] = "-"
                continue

            if row["expected_seconds"]:
                exp = round(row["expected_seconds"], 1) if row["expected_seconds"] is not None else None
                row["expected_seconds"] = exp
                act = row["actual_seconds"]
                if exp:
                    row["percent"] = round((act / exp) * 100.0, 1)
                    # Apply thresholds; skip warnings if actual is very short.
                    if act >= 2.0:
                        if act < self.too_short * exp and exp >= 1.0:
                            row["warning"] = "<"
                        elif act > self.too_long * exp:
                            row["warning"] = ">"
                    if row["warning"]:
                        logging.warning(
                            "%s %s duration off: actual %.2fs vs expected %.2fs",
                            role,
                            row["id"],
                            act,
                            exp,
                        )

        def sort_key(row: Dict):
            pid, bid, sid = parse_id(row["id"])
            part = pid if pid is not None else -1
            block = bid if bid is not None else -1
            seg = sid if sid is not None else -1
            return (part, block, seg)

        rows.sort(key=sort_key)
        return rows

    def _build_plan_start_map(self) -> None:
        """Build a mapping clip_id -> start seconds using the provided plan."""
        for item in self.plan:
            if not hasattr(item, "clip_id") or not getattr(item, "clip_id"):
                continue
            clip_id = str(getattr(item, "clip_id"))
            # Clip ids in plans use ':' separators; convert to '_' to match segment filenames/ids.
            norm_id = clip_id.replace(":", "_")
            self._plan_start_map[norm_id] = round(getattr(item, "offset_ms", 0) / 1000.0, 1)

    def _load_offsets(self) -> None:
        """Load source offsets from per-role offsets.txt files."""
        if not SEGMENTS_DIR.exists():
            return
        for role_dir in SEGMENTS_DIR.iterdir():
            if not role_dir.is_dir():
                continue
            offsets_path = role_dir / "offsets.txt"
            if not offsets_path.exists():
                continue
            role_offsets: Dict[str, str] = {}
            for line in offsets_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                seg_id, ts = parts[0], parts[1]
                role_offsets[seg_id.replace(":", "_")] = ts
            self._offsets_map[role_dir.name] = role_offsets

    @staticmethod
    def _parse_timecode(ts: str) -> float | None:
        """Parse m:ss.s or seconds strings into float seconds."""
        try:
            if ":" in ts:
                mins, secs = ts.split(":", 1)
                return float(mins) * 60 + float(secs)
            return float(ts)
        except ValueError:
            return None

    @staticmethod
    def _format_seconds(seconds: float | None) -> str | None:
        """Format seconds into m:ss.t with tenths precision."""
        if seconds is None:
            return None
        mins = int(seconds // 60)
        secs = seconds - mins * 60
        return f"{mins}:{secs:04.1f}"


if __name__ == "__main__":
    play = PlayTextParser().parse()
    builder = PlayPlanBuilder(play_text=play)
    plan, _ = builder.build_audio_plan(parts=builder.list_parts())
    SegmentVerifier(plan=plan).verify_segments()


# Backwards-compatible helper to compute rows directly.
def compute_rows(too_short: float = 0.5, too_long: float = 2.0) -> List[Dict]:
    play = PlayTextParser().parse()
    builder = PlayPlanBuilder(play_text=play)
    plan, _ = builder.build_audio_plan(parts=builder.list_parts())
    verifier = SegmentVerifier(plan=plan, too_short=too_short, too_long=too_long, play_text=play)
    return verifier.compute_rows()
