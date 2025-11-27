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
            id_part, role = raw.split()
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


def build_part_audio(
    part_filter: int | None,
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
) -> Path:
    """Stitch snippets for a given part (or None for preamble) into one WAV."""
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

    AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)
    if part_filter is None:
        out_path = AUDIO_OUT_DIR / "preamble.wav"
    else:
        out_path = AUDIO_OUT_DIR / f"part_{part_filter}.wav"
    combined.export(out_path, format="wav")
    logging.info("Wrote %s (%d segments)", out_path, len(ordered_ids))
    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Assemble play audio by part.")
    parser.add_argument("--part", required=True, help="Part number, or '_' for no-part blocks")
    parser.add_argument("--segment-spacing-ms", type=int, default=0, help="Silence inserted between snippets")
    args = parser.parse_args()
    part_arg = None if args.part == "_" else int(args.part)
    build_part_audio(part_arg, spacing_ms=args.segment_spacing_ms)
