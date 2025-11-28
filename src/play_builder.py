#!/usr/bin/env python3
"""Assemble per-part audio by stitching together split snippets in index order."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple
from functools import lru_cache

from pydub import AudioSegment
import re    
from narrator_splitter import parse_narrator_blocks
from paths import (
    AUDIO_OUT_DIR, 
    SEGMENTS_DIR, 
    BLOCKS_DIR, 
    BLOCKS_EXT, 
    INDEX_PATH, 
    CALLOUTS_DIR,
    AUDIO_PLAY_DIR,
    PARAGRAPHS_PATH
    )


IndexEntry = Tuple[int | None, int, str]  # (part, block, role)
BlockMap = Dict[Tuple[int | None, int], List[str]]

PART_HEADING_RE = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
META_RE = re.compile(r"^::(.*)::$")
DESCRIPTION_RE = re.compile(r"^\[\[(.*)\]\]$")
STAGE_RE = re.compile(r"^_+(.*?)_+\s*$")
BLOCK_RE = re.compile(r"^[A-Z][A-Z '()-]*?\.\s*.*$")


def read_block_bullets(role: str, part: int | None, block: int) -> List[str]:
    """Return bullet texts for the given role/part/block in source order."""
    path = BLOCKS_DIR / f"{role}{BLOCKS_EXT}"
    if not path.exists():
        logging.warning("Block file missing for %s: %s", role, path)
        return []

    target_head = f"{'' if part is None else part}:{block}"
    in_block = False
    bullets: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped[0].isdigit() or stripped.startswith(":"):
            head = stripped.split()[0]
            if in_block and head != target_head:
                break  # left the block
            in_block = head == target_head
            continue
        if in_block and stripped.startswith("-"):
            bullets.append(stripped[1:].strip())
    return bullets


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


def load_description_callout() -> AudioSegment | None:
    """Load the description callout (_DESCRIPTION.wav) if present."""
    path = CALLOUTS_DIR / "_DESCRIPTION.wav"
    if not path.exists():
        logging.warning("Description callout missing: %s", path)
        return None
    return AudioSegment.from_file(path)


@lru_cache(maxsize=1)
def description_block_keys() -> set[Tuple[int, int]]:
    """
    Return (part, block) pairs that correspond to description paragraphs ([[...]])
    so we can limit description callouts to true descriptions (not titles or meta).
    """
    keys: set[Tuple[int, int]] = set()
    current_part: int | None = None
    block_counter = 0
    for line in PARAGRAPHS_PATH.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = PART_HEADING_RE.match(stripped)
        if heading:
            current_part = int(heading.group(1))
            block_counter = 0
            continue
        if META_RE.match(stripped):
            continue  # meta lines do not advance block numbering
        if current_part is None:
            continue
        if DESCRIPTION_RE.match(stripped):
            block_counter += 1
            keys.add((current_part, block_counter))
            continue
        if STAGE_RE.match(stripped) or BLOCK_RE.match(stripped):
            block_counter += 1
            continue
    return keys


def build_block_audio_segment(
    part_filter: int | None,
    block_no: int,
    roles_in_block: List[str],
    seg_maps: Dict[str, BlockMap],
    *,
    silence: AudioSegment | None,
    callout_gap: AudioSegment | None,
    include_callouts: bool,
    minimal_callouts: bool,
    include_description_callouts: bool,
    description_blocks: set[Tuple[int, int]],
    callout_cache: Dict[str, AudioSegment | None],
    description_callout: AudioSegment | None,
    seen_roles: set[str],
    prev_role: str | None,
    prev2_role: str | None,
    last_callout_type: str | None,
    is_last_block: bool,
) -> tuple[
    AudioSegment,
    str | None,
    str | None,
    str | None,
    AudioSegment | None,
    set[str],
]:
    """Build audio for a single block, including optional callouts."""
    block_audio = AudioSegment.empty()
    primary_role = next((r for r in roles_in_block if r != "_NARRATOR"), None)
    is_description = part_filter is not None and (part_filter, block_no) in description_blocks

    # Description callout for narrator-only description blocks.
    if include_description_callouts and primary_role is None and is_description:
        if description_callout is None:
            description_callout = load_description_callout()
        if description_callout and last_callout_type != "description":
            block_audio += description_callout
            if callout_gap:
                block_audio += callout_gap
            last_callout_type = "description"

    # Role callout before any block audio.
    if include_callouts and primary_role:
        need_callout = True
        if minimal_callouts and primary_role in seen_roles:
            if primary_role == prev_role:
                need_callout = False
            elif prev2_role == primary_role and prev_role and prev_role != primary_role:
                need_callout = False
        if need_callout:
            if primary_role not in callout_cache:
                callout_cache[primary_role] = load_callout(primary_role)
            call = callout_cache[primary_role]
            if call:
                block_audio += call
                if callout_gap:
                    block_audio += callout_gap
                last_callout_type = "role"
            seen_roles.add(primary_role)

    # Append block content in paragraph order.
    block_segments: List[Tuple[str, str]] = []
    source_role = primary_role or roles_in_block[0]
    bullets = read_block_bullets(source_role, part_filter, block_no)
    if bullets:
        for idx, text in enumerate(bullets, start=1):
            owner = "_NARRATOR" if primary_role is not None and text.startswith("(_") else (primary_role or "_NARRATOR")
            sid = f"{'' if part_filter is None else part_filter}_{block_no}_{idx}"
            block_segments.append((owner, sid))
    else:
        # Fallback to existing segment ordering if we couldn't read bullets.
        for role in roles_in_block:
            seg_ids = seg_maps.get(role, {}).get((part_filter, block_no), [])
            if not seg_ids:
                logging.warning("No segment ids for %s %s:%s", role, part_filter, block_no)
            for sid in seg_ids:
                block_segments.append((role, sid))

    for seg_idx, (role, seg_id) in enumerate(block_segments):
        wav_path = SEGMENTS_DIR / role / f"{seg_id}.wav"
        if not wav_path.exists():
            logging.error("Missing snippet %s for role %s", seg_id, role)
            continue
        block_audio += AudioSegment.from_file(wav_path)
        is_last_seg = seg_idx == len(block_segments) - 1
        if silence and not (is_last_block and is_last_seg):
            block_audio += silence
        if role != "_NARRATOR":
            prev2_role, prev_role = prev_role, role

    return block_audio, prev_role, prev2_role, last_callout_type, description_callout, seen_roles

def extract_blocks(entries: List[IndexEntry], part_filter: int|None) -> List[Tuple[int, List[str]]]:
    # Group entries by block to keep callouts preceding block audio.
    block_entries: List[Tuple[int, List[str]]] = []
    current_block: int | None = None
    current_roles: List[str] = []
    for part, block, role in entries:
        if part != part_filter:
            continue
        if current_block is None or block != current_block:
            if current_block is not None:
                block_entries.append((current_block, current_roles))
            current_block = block
            current_roles = []
        current_roles.append(role)
    if current_block is not None:
        block_entries.append((current_block, current_roles))

    if not block_entries:
        raise RuntimeError(f"No segments found for part {part_filter!r}")
    
    return block_entries

def build_part_audio_segment(
    part_filter: int | None,
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
    include_description_callouts: bool = True,
) -> AudioSegment:
    """Stitch snippets for a given part (or None for preamble) into one AudioSegment."""
    silence = AudioSegment.silent(duration=spacing_ms) if spacing_ms > 0 else None
    callout_gap = AudioSegment.silent(duration=callout_spacing_ms) if callout_spacing_ms > 0 else None
    entries = parse_index()
    seg_maps = load_segment_maps()
    callout_cache: Dict[str, AudioSegment | None] = {}
    description_callout: AudioSegment | None = None
    description_blocks = description_block_keys()

    block_entries = extract_blocks(entries, part_filter)

    combined = AudioSegment.empty()
    prev_role: str | None = None
    prev2_role: str | None = None
    seen_roles: set[str] = set()
    last_callout_type: str | None = None

    for b_idx, (block_no, roles_in_block) in enumerate(block_entries):
        block_audio, prev_role, prev2_role, last_callout_type, description_callout, seen_roles = build_block_audio_segment(
            part_filter,
            block_no,
            roles_in_block,
            seg_maps,
            silence=silence,
            callout_gap=callout_gap,
            include_callouts=include_callouts,
            minimal_callouts=minimal_callouts,
            include_description_callouts=include_description_callouts,
            description_blocks=description_blocks,
            callout_cache=callout_cache,
            description_callout=description_callout,
            seen_roles=seen_roles,
            prev_role=prev_role,
            prev2_role=prev2_role,
            last_callout_type=last_callout_type,
            is_last_block=b_idx == len(block_entries) - 1,
        )
        combined += block_audio

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


def load_part_titles() -> Dict[int, str]:
    titles: Dict[int, str] = {}
    # read from paragraphs to get headings

    heading_re = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
    for line in PARAGRAPHS_PATH.read_text(encoding="utf-8-sig").splitlines():
        if not titles:
            titles[None] = re.match("^::(.*)::$", line).groups()[0].strip().replace(" ", "_")
            continue
        m = heading_re.match(line.strip())
        if m:
            pid = int(m.group(1))
            titles[pid] = m.group(2).strip().replace(" ", "_")
    return titles

def compute_output_path(parts: List[int | None], part: int, audio_format: str = "mp4") -> Path:
    titles = load_part_titles()
    if part is None:
        title = titles.get(None, "play")
    else: 
        title = f"{part}_{titles.get(part, "part")}"
    return AUDIO_PLAY_DIR / f"{title}.{audio_format}"

def build_audio(
    parts: List[int | None],
    part: int | None = None,
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
    include_description_callouts: bool = True,
    audio_format: str = "mp4",
    part_chapters: bool = False,
    part_gap_ms: int = 0,
) -> Path:
    out_path = compute_output_path(parts, part, audio_format)
    logging.info("Generating audioplay to %s", out_path)
    combined = AudioSegment.empty()
    chapters: List[Tuple[int, int, str]] = []
    for part in parts:
        logging.info("Building part %s", "PREAMBLE" if part is None else part)
        part_start = len(combined)
        seg = build_part_audio_segment(
            part_filter=part,
            spacing_ms=spacing_ms,
            include_callouts=include_callouts,
            callout_spacing_ms=callout_spacing_ms,
            minimal_callouts=minimal_callouts,
            include_description_callouts=include_description_callouts,
        )
        combined += seg
        part_end = len(combined)
        if part_chapters:
            title = "PREAMBLE" if part is None else f"PART {part}"
            chapters.append((part_start, part_end, title))
        if part_gap_ms and part != parts[-1]:
            combined += AudioSegment.silent(duration=part_gap_ms)
    ext = "mp4" if audio_format == "mp4" else audio_format
    export_with_chapters(combined, chapters if part_chapters else [], out_path, fmt=audio_format)
    logging.info("Wrote %s", out_path)
    return out_path
