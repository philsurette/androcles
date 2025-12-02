#!/usr/bin/env python3
"""Build role cue MP4s with chapter markers for cues and responses."""
from __future__ import annotations

import argparse
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from pydub import AudioSegment

from play_text import PlayTextParser
from play_plan_builder import load_segment_maps
from paths import SEGMENTS_DIR, AUDIO_OUT_DIR


def concat_segments(role: str, seg_ids: List[str]) -> AudioSegment:
    audio = AudioSegment.empty()
    for sid in seg_ids:
        path = SEGMENTS_DIR / role / f"{sid}.wav"
        if not path.exists():
            logging.warning("Missing snippet %s for role %s", sid, role)
            continue
        audio += AudioSegment.from_file(path)
    return audio


def crop_cue(
    audio: AudioSegment,
    tail_ms: int = 5000,
    extend_ms: int = 2000,
    head_ms: int = 2000,
    gap_ms: int = 500,
) -> AudioSegment:
    """
    Keep the last `tail_ms` (configurable). If the total cue is shorter than
    tail_ms + extend_ms, keep it whole. Otherwise keep the first `head_ms`,
    a gap, then the last `tail_ms`.
    """
    total = len(audio)
    if total <= tail_ms + extend_ms:
        return audio
    head = audio[: min(head_ms, total)]
    tail = audio[-tail_ms:] if tail_ms < total else audio
    gap = AudioSegment.silent(duration=gap_ms) if gap_ms > 0 else AudioSegment.empty()
    return head + gap + tail


def build_cues_for_role(
    role: str,
    response_delay_ms: int = 2000,
    max_cue_size_ms: int = 5000,
    include_prompts: bool = True,
    callout_spacing_ms: int = 300,
) -> Tuple[AudioSegment, List[Tuple[int, int, str]]]:
    """
    Return combined audio and chapter tuples (start_ms, end_ms, title)
    for the given role.
    """
    play = PlayTextParser().parse()
    entries = play.to_index_entries()
    seg_maps = load_segment_maps(play)

    combined = AudioSegment.empty()
    chapters: List[Tuple[int, int, str]] = []
    callout_cache: Dict[str, AudioSegment | None] = {}
    callout_gap = AudioSegment.silent(duration=callout_spacing_ms) if callout_spacing_ms > 0 else None

    # Build mapping for quick lookup
    # entries already in order; find previous block per part
    idx_by_part: Dict[int | None, List[Tuple[int, int, str]]] = {}
    for part, block, r in entries:
        idx_by_part.setdefault(part, []).append((block, r))

    for i, (part, block, r) in enumerate(entries):
        if r != role:
            continue
        # find previous speech entry (non-narrator) in same part
        prev_entry = None
        for j in range(i - 1, -1, -1):
            p_prev, b_prev, r_prev = entries[j]
            if p_prev == part and r_prev != "_NARRATOR":
                prev_entry = (p_prev, b_prev, r_prev)
                break

        if prev_entry and include_prompts:
            cue_part, cue_block, cue_role = prev_entry
            cue_ids = seg_maps.get(cue_role, {}).get((cue_part, cue_block), [])
            if cue_ids:
                # Optional callout before prompt
                if cue_role not in callout_cache:
                    callout_cache[cue_role] = load_callout(cue_role)
                call = callout_cache[cue_role]
                if call:
                    combined += call
                    if callout_gap:
                        combined += callout_gap

                cue_audio = concat_segments(cue_role, cue_ids)
                cue_audio = crop_cue(cue_audio, tail_ms=max_cue_size_ms)

                cue_start = len(combined)
                combined += cue_audio
                cue_end = len(combined)
                chapters.append((cue_start, cue_end, f"CUE {cue_role} {cue_ids[0]}"))

                # gap before response
                combined += AudioSegment.silent(duration=response_delay_ms)
        else:
            # first speech in part: no cue, no leading gap
            pass

        resp_ids = seg_maps.get(role, {}).get((part, block), [])
        if not resp_ids:
            logging.warning("No response segment ids for %s %s:%s", role, part, block)
            continue
        resp_audio = concat_segments(role, resp_ids)
        resp_start = len(combined)
        combined += resp_audio
        resp_end = len(combined)
        chapters.append((resp_start, resp_end, f"LINE {role} {resp_ids[0]}"))

        # gap before next cue unless this is last
        combined += AudioSegment.silent(duration=response_delay_ms)

    return combined, chapters


def write_ffmetadata(chapters: List[Tuple[int, int, str]], path: Path) -> None:
    lines = [";FFMETADATA1"]
    for start, end, title in chapters:
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={start}")
        lines.append(f"END={end}")
        lines.append(f"title={title}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_mp4(audio: AudioSegment, chapters: List[Tuple[int, int, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "tmp.wav"
        meta_path = Path(tmpdir) / "chapters.txt"
        audio.export(wav_path, format="wav")
        write_ffmetadata(chapters, meta_path)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-i",
            str(meta_path),
            "-map_metadata",
            "1",
            "-c:a",
            "aac",
            str(out_path),
        ]
        subprocess.run(cmd, check=True)


def build_cues(
    role: str,
    response_delay_ms: int = 2000,
    max_cue_size_ms: int = 5000,
    include_prompts: bool = True,
    callout_spacing_ms: int = 300,
) -> Path:
    audio, chapters = build_cues_for_role(
        role,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
    )
    # drop trailing silence from last gap if present
    if chapters:
        total = chapters[-1][1]
        audio = audio[:total]
    out_path = AUDIO_OUT_DIR / "cues" / f"{role}_cue.mp4"
    export_mp4(audio, chapters, out_path)
    logging.info("Wrote cue file %s with %d chapters", out_path, len(chapters))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a chapterized cue MP4 for a role.")
    parser.add_argument("role", help="Role name (e.g., ANDROCLES)")
    parser.add_argument("--response-delay-ms", type=int, default=2000, help="Silence between cue and response (ms)")
    parser.add_argument(
        "--max-cue-size-ms",
        type=int,
        default=5000,
        help="Max length of a cue; longer cues are cropped with head+tail (ms)",
    )
    args = parser.parse_args()
    build_cues(args.role, response_delay_ms=args.response_delay_ms, max_cue_size_ms=args.max_cue_size_ms)


# Note: command-line handling is done in build.py
