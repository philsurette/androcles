#!/usr/bin/env python3
"""Verify split audio segments."""
from __future__ import annotations

import logging
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Iterable

from pydub import AudioSegment

import paths
from play_plan_builder import PlayPlanBuilder
from play import Play
from play_text_parser import PlayTextParser
from segment import  MetaSegment, DescriptionSegment, DirectionSegment, SpeechSegment, SimultaneousSegment
from block import RoleBlock, TitleBlock, DescriptionBlock, DirectionBlock
from clip import Clip, CalloutClip, ParallelClips, Silence
from spacing import CALLOUT_SPACING_MS, SEGMENT_SPACING_MS

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
    play: Play | None = None
    part_no: int | None = None
    include_decorations: bool = False
    paths: paths.PathConfig = field(default_factory=paths.current)
    _plan_start_map: Dict[str, float] = field(init=False, default_factory=dict)
    _offsets_map: Dict[str, Dict[str, str]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.play is None:
            self.play = PlayTextParser(paths_config=self.paths).parse()
        self._build_plan_start_map()
        self._load_offsets()

    def gather_expected(self) -> List[Dict]:
        rows: List[Dict] = []
        if self.play is None:
            return rows
        # Narrator/meta content
        rows.extend(self._gather_narrator_segments())

        # Roles (skip narrator to avoid double counting)
        for role_obj in self.play.getRoles():
            role = role_obj.name
            if role == "_NARRATOR":
                continue
            for blk in role_obj.blocks:
                if self.part_no is not None and blk.block_id.part_id != self.part_no:
                    continue
                seq = 0
                for seg in blk.segments:
                    text = getattr(seg, "text", "").strip()
                    if not text or text in {".", ",", ":", ";"}:
                        continue
                    seq += 1
                    if (isinstance(seg, SpeechSegment) and seg.role == role) or (
                        isinstance(seg, SimultaneousSegment) and role in getattr(seg, "roles", [])
                    ):
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
        if self.play is None:
            return rows

        for blk in self.play.blocks:
            if self.part_no is not None and blk.block_id.part_id != self.part_no:
                continue
            if isinstance(blk, (TitleBlock, DescriptionBlock, DirectionBlock)):
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
            fpath = self.paths.segments_dir / role / f"{row['id']}.wav"
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
                    # Apply thresholds; short clips only warn when far below expected.
                    if act >= 2.0:
                        if act < self.too_short * exp and exp >= 1.0:
                            row["warning"] = "<"
                        elif act > self.too_long * exp:
                            row["warning"] = ">"
                    elif exp - act > 3.0:
                        row["warning"] = "<"
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

        if self.include_decorations:
            return self._merge_decorations(rows)

        rows.sort(key=sort_key)
        return rows

    def _build_plan_start_map(self) -> None:
        """Build a mapping clip_id -> start seconds using the provided plan."""
        for item in self.plan:
            if hasattr(item, "clips"):
                for clip in getattr(item, "clips", []):
                    clip_id = getattr(clip, "clip_id", None)
                    if not clip_id:
                        continue
                    norm_id = str(clip_id).replace(":", "_")
                    self._plan_start_map[norm_id] = round(getattr(clip, "offset_ms", 0) / 1000.0, 1)
                continue
            if not hasattr(item, "clip_id") or not getattr(item, "clip_id"):
                continue
            clip_id = str(getattr(item, "clip_id"))
            # Clip ids in plans use ':' separators; convert to '_' to match segment filenames/ids.
            norm_id = clip_id.replace(":", "_")
            self._plan_start_map[norm_id] = round(getattr(item, "offset_ms", 0) / 1000.0, 1)

    def _load_offsets(self) -> None:
        """Load source offsets from per-role offsets.txt files."""
        if not self.paths.segments_dir.exists():
            return
        for role_dir in self.paths.segments_dir.iterdir():
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

    def _merge_decorations(self, rows: List[Dict]) -> List[Dict]:
        expected_by_id = {row["id"]: row for row in rows}
        seen: set[str] = set()
        merged: List[Dict] = []
        decor_index = 0
        for clip in self._iter_plan_clips():
            norm_id = None
            if clip.clip_id:
                norm_id = str(clip.clip_id).replace(":", "_")
            if norm_id and norm_id in expected_by_id:
                if norm_id in seen:
                    continue
                merged.append(expected_by_id[norm_id])
                seen.add(norm_id)
                continue
            decor_index += 1
            merged.append(self._build_decoration_row(clip, decor_index))
        for row in rows:
            if row["id"] not in seen:
                merged.append(row)
        return merged

    def _iter_plan_clips(self) -> Iterable[Clip]:
        for item in self.plan:
            if isinstance(item, ParallelClips):
                for clip in item.clips:
                    if not isinstance(clip, Silence):
                        yield clip
                continue
            if isinstance(item, Clip) and not isinstance(item, Silence):
                yield item

    def _build_decoration_row(self, clip: Clip, index: int) -> Dict:
        text = clip.text or ""
        if not text:
            if clip.clip_id:
                text = str(clip.clip_id)
            elif clip.path is not None:
                text = clip.path.stem
        actual_seconds = round(clip.length_ms / 1000.0, 1)
        start_sec = round(clip.offset_ms / 1000.0, 1)
        return {
            "id": f"decor_{index:04d}",
            "warning": "",
            "expected_seconds": None,
            "actual_seconds": actual_seconds,
            "percent": None,
            "start": self._format_seconds(start_sec),
            "src_offset": "",
            "role": self._decoration_role(clip),
            "text": text,
        }

    def _decoration_role(self, clip: Clip) -> str:
        if isinstance(clip, CalloutClip):
            return "_CALLER"
        if clip.path is not None and clip.path.parent.name == "_ANNOUNCER":
            return "_ANNOUNCER"
        return clip.role or "_DECOR"


if __name__ == "__main__":
    play = PlayTextParser().parse()
    builder = PlayPlanBuilder(play=play)
    plan = builder.build_audio_plan(parts=builder.list_parts())
    SegmentVerifier(plan=plan).verify_segments()


# Backwards-compatible helper to compute rows directly.
def compute_rows(
        too_short: float = 0.5, 
        too_long: float = 2.0,
        librivox: bool = False,
        part_no: int | None = None,
        include_callouts: bool = False,
        callout_spacing_ms: int = CALLOUT_SPACING_MS,
        minimal_callouts: bool = False,
        segment_spacing_ms: int = SEGMENT_SPACING_MS,
        include_decorations: bool = False,
        paths_config: paths.PathConfig | None = None,
    ) -> List[Dict]:
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    from callout_director import (
        ConversationAwareCalloutDirector,
        RoleCalloutDirector,
        NoCalloutDirector,
    )

    if include_callouts:
        if minimal_callouts:
            director = ConversationAwareCalloutDirector(play)
        else:
            director = RoleCalloutDirector(play, paths_config=cfg)
    else:
        director = NoCalloutDirector(play, paths_config=cfg)

    builder = PlayPlanBuilder(
        play=play,
        librivox=librivox,
        paths=cfg,
        director=director,
        segment_spacing_ms=segment_spacing_ms,
        include_callouts=include_callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
    )
    plan = builder.build_audio_plan(part_no=part_no)
    verifier = SegmentVerifier(
        plan=plan,
        too_short=too_short,
        too_long=too_long,
        play=play,
        part_no=part_no,
        include_decorations=include_decorations,
        paths=cfg,
    )
    return verifier.compute_rows()
