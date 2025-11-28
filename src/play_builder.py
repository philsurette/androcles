#!/usr/bin/env python3
"""Assemble per-part audio by stitching together split snippets in index order."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from pydub import AudioSegment

from narrator_splitter import parse_narrator_blocks
from paths import AUDIO_OUT_DIR, BLOCKS_DIR, BLOCKS_EXT, INDEX_PATH, CALLOUTS_DIR


IndexEntry = Tuple[int | None, int, str]  # (part, block, role)
BlockMap = Dict[Tuple[int | None, int], List[str]]


def parse_index() -> List[IndexEntry]:
    """Read INDEX.files and return ordered (part, block, role) tuples."""
    entries: List[IndexEntry] = []
    for raw in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            id_part, role = raw.split(maxsplit=1)
        except ValueError:
            continue
        if id_part.startswith(":"):
            part = None
            block = int(id_part[1:])
        else:
            p_str, b_str = id_part.split(":", 1)
            part = int(p_str)
            block = int(b_str)
        entries.append((part, block, role))
    return entries


def parse_role_blocks(role: str) -> BlockMap:
    """Return mapping (part, block) -> ordered segment ids for a role (speech only)."""
    path = BLOCKS_DIR / f"{role}{BLOCKS_EXT}"
    mapping: BlockMap = {}
    if not path.exists():
        logging.warning("Blocks file missing for role %s: %s", role, path)
        return mapping

    current_part: int | None = None
    current_block: int | None = None
    elem_idx = 0

    def add_seg(text: str) -> None:
        nonlocal elem_idx
        elem_idx += 1
        if text.startswith("(_"):
            return  # directions are narration
        if current_block is None:
            return
        key = (current_part, current_block)
        mapping.setdefault(key, []).append(f"{current_part}_{current_block}_{elem_idx}")

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped[0].isdigit() or stripped.startswith(":"):
            head = stripped.split()[0]
            if ":" in head:
                p_str, b_str = head.split(":", 1)
                current_part = int(p_str) if p_str else None
                current_block = int(b_str)
                elem_idx = 0
            continue
        if stripped.startswith("-"):
            add_seg(stripped[1:].strip())

    return mapping


def parse_narrator_map() -> BlockMap:
    mapping: BlockMap = {}
    for eid, _text in parse_narrator_blocks():
        parts = eid.split("_")
        if len(parts) == 3:
            part = int(parts[0]) if parts[0] else None
            block = int(parts[1])
        elif len(parts) == 2:  # no-part meta
            part = None
            block = int(parts[0])
        else:
            continue
        mapping.setdefault((part, block), []).append(eid)
    return mapping


def load_segment_maps() -> Dict[str, BlockMap]:
    """Build segment-id maps for all roles present in the index."""
    maps: Dict[str, BlockMap] = {}
    for _, _, role in parse_index():
        if role in maps:
            continue
        if role == "_NARRATOR":
            maps[role] = parse_narrator_map()
        else:
            maps[role] = parse_role_blocks(role)
    return maps


def load_callout(role: str) -> AudioSegment | None:
    path = CALLOUTS_DIR / f"{role}_callout.wav"
    if not path.exists():
        logging.warning("Callout missing for role %s: %s", role, path)
        return None
    return AudioSegment.from_file(path)


def build_part_audio_segment(
    part_filter: int | None,
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
) -> AudioSegment:
    """Stitch snippets for a given part (or None for preamble) into one AudioSegment."""
    silence = AudioSegment.silent(duration=spacing_ms) if spacing_ms > 0 else None
    callout_gap = AudioSegment.silent(duration=callout_spacing_ms) if callout_spacing_ms > 0 else None
    entries = parse_index()
    seg_maps = load_segment_maps()
    callout_cache: Dict[str, AudioSegment | None] = {}

    ordered_ids: List[Tuple[str, int, str]] = []  # (role, block, seg_id)
    for part, block, role in entries:
        if part != part_filter:
            continue
        seg_ids = seg_maps.get(role, {}).get((part, block), [])
        if not seg_ids:
            logging.warning("No segment ids for %s %s:%s", role, part, block)
        for sid in seg_ids:
            ordered_ids.append((role, block, sid))

    if not ordered_ids:
        raise RuntimeError(f"No segments found for part {part_filter!r}")

    combined = AudioSegment.empty()
    last_block_key: Tuple[str, int] | None = None
    prev_role: str | None = None
    prev2_role: str | None = None
    seen_roles: set[str] = set()
    for idx, (role, block, seg_id) in enumerate(ordered_ids):
        wav_path = AUDIO_OUT_DIR / role / f"{seg_id}.wav"
        if not wav_path.exists():
            logging.error("Missing snippet %s for role %s", seg_id, role)
            continue
        if include_callouts and role != "_NARRATOR":
            block_key = (role, block)
            if block_key != last_block_key:
                need_callout = True
                if minimal_callouts:
                    if role in seen_roles:
                        if role == prev_role:
                            need_callout = False
                        elif prev2_role == role and prev_role and prev_role != role:
                            # simple alternating dialogue with two roles
                            need_callout = False
                if need_callout:
                    if role not in callout_cache:
                        callout_cache[role] = load_callout(role)
                    call = callout_cache[role]
                    if call:
                        combined += call
                        if callout_gap:
                            combined += callout_gap
                last_block_key = block_key
                seen_roles.add(role)
        combined += AudioSegment.from_file(wav_path)
        if silence and idx < len(ordered_ids) - 1:
            combined += silence
        if role != "_NARRATOR":
            prev2_role, prev_role = prev_role, role

    return combined


def export_with_chapters(audio: AudioSegment, chapters: List[Tuple[int, int, str]], out_path: Path, fmt: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "wav" or not chapters:
        audio.export(out_path, format=fmt)
        return

    # Use ffmpeg to embed chapter metadata
    import tempfile
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "tmp.wav"
        meta_path = Path(tmpdir) / "chapters.txt"
        audio.export(wav_path, format="wav")
        lines = [";FFMETADATA1"]
        for start, end, title in chapters:
            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={start}")
            lines.append(f"END={end}")
            lines.append(f"title={title}")
        meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
            "aac" if fmt == "mp4" else "libmp3lame",
            str(out_path),
        ]
        subprocess.run(cmd, check=True)


def list_parts() -> List[int | None]:
    parts: List[int | None] = []
    for p, _, _ in parse_index():
        if p not in parts:
            parts.append(p)
    # sort with None (preamble) first
    parts_sorted = sorted([x for x in parts if x is not None])
    if None in parts:
        return [None] + parts_sorted
    return parts_sorted


def build_audio(
    parts: List[int | None],
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
    audio_format: str = "mp4",
    part_chapters: bool = False,
    part_gap_ms: int = 0,
) -> Path:
    combined = AudioSegment.empty()
    chapters: List[Tuple[int, int, str]] = []
    for part in parts:
        part_start = len(combined)
        seg = build_part_audio_segment(
            part_filter=part,
            spacing_ms=spacing_ms,
            include_callouts=include_callouts,
            callout_spacing_ms=callout_spacing_ms,
            minimal_callouts=minimal_callouts,
        )
        combined += seg
        part_end = len(combined)
        if part_chapters:
            title = "PREAMBLE" if part is None else f"PART {part}"
            chapters.append((part_start, part_end, title))
        if part_gap_ms and part != parts[-1]:
            combined += AudioSegment.silent(duration=part_gap_ms)
    ext = "mp4" if audio_format == "mp4" else audio_format
    if len(parts) == 1:
        part = parts[0]
        if part is None:
            out_path = AUDIO_OUT_DIR / f"preamble.{ext}"
        else:
            out_path = AUDIO_OUT_DIR / f"part_{part}.{ext}"
    else:
        out_path = AUDIO_OUT_DIR / f"play.{ext}"
    export_with_chapters(combined, chapters if part_chapters else [], out_path, fmt=audio_format)
    logging.info("Wrote %s", out_path)
    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Assemble play audio by part.")
    parser.add_argument("--part", required=True, help="Part number, or '_' for no-part blocks")
    parser.add_argument("--segment-spacing-ms", type=int, default=0, help="Silence inserted between snippets")
    args = parser.parse_args()
    part_arg = None if args.part == "_" else int(args.part)
    build_part_audio(part_arg, spacing_ms=args.segment_spacing_ms)
