#!/usr/bin/env python3
"""Build audio plans for the play."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import logging
import re
from typing import Dict, List, Tuple, Union

from pydub import AudioSegment

from narrator_splitter import parse_narrator_blocks
from chapter_builder import Chapter, ChapterBuilder
from clip import SegmentClip, CalloutClip, SegmentClip, Silence
from audio_plan import AudioPlan, PlanItem
from paths import (
    AUDIO_OUT_DIR,
    BLOCKS_DIR,
    BLOCKS_EXT,
    INDEX_PATH,
    CALLOUTS_DIR,
    AUDIO_PLAY_DIR,
    PARAGRAPHS_PATH,
    SEGMENTS_DIR
)


IndexEntry = Tuple[int | None, int, str]
BlockMap = Dict[Tuple[int | None, int], List[str]]

PART_HEADING_RE = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
META_RE = re.compile(r"^::(.*)::$")
DESCRIPTION_RE = re.compile(r"^\[\[(.*)\]\]$")
STAGE_RE = re.compile(r"^_+(.*?)_+\s*$")
BLOCK_RE = re.compile(r"^[A-Z][A-Z '()-]*?\.\s*.*$")

INTER_WORD_PAUSE_MS = 300

def parse_index() -> List[IndexEntry]:
    """Read INDEX.files and return ordered (part, block, role) tuples."""
    entries: List[IndexEntry] = []
    for raw in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        id_part, role = raw.split(maxsplit=1)

        if id_part.startswith(":"):
            part = None
            block = int(id_part[1:])
        else:
            p_str, b_str = id_part.split(":", 1)
            part = int(p_str)
            block = int(b_str)
        entries.append((part, block, role))
    return entries


def parse_block_file(path: Path) -> Dict[Tuple[str, str], List[str]]:
    """Return a mapping {(part_id, block_no): [lines]} for a block file."""
    content: Dict[Tuple[str, str], List[str]] = {}
    current_key: Tuple[str, str] | None = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            content[current_key] = current_lines
        current_key = None
        current_lines = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip() and (raw_line.strip()[0].isdigit() or raw_line.strip().startswith(":")):
            flush()
            part_id, block_no = raw_line.strip().split(":")
            current_key = (part_id, block_no)
            current_lines = [raw_line.strip()]
        else:
            if current_key is not None:
                current_lines.append(raw_line)

    flush()
    return content


def load_blocks() -> Dict[str, Dict[Tuple[str, str], List[str]]]:
    """Load all block files into a mapping by target name."""
    blocks: Dict[str, Dict[Tuple[str, str], List[str]]] = {}
    for path in BLOCKS_DIR.glob(f"*{BLOCKS_EXT}"):
        if path.name == f"_INDEX{BLOCKS_EXT}":
            continue
        blocks[path.stem] = parse_block_file(path)
    return blocks


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


def load_audio_by_path(path: Path, cache: Dict[Path, AudioSegment | None]) -> AudioSegment | None:
    """Load audio by path with caching."""
    if path in cache:
        return cache[path]
    if not path.exists():
        logging.warning("Audio file missing: %s", path)
        cache[path] = None
        return None
    audio = AudioSegment.from_file(path)
    cache[path] = audio
    return audio


def get_audio_length_ms(path: Path, cache: Dict[Path, int]) -> int:
    """Return audio length in ms, caching results (0 if missing)."""
    if path in cache:
        return cache[path]
    if not path.exists():
        logging.warning("Audio file missing: %s", path)
        cache[path] = 0
        return 0
    length = len(AudioSegment.from_file(path))
    cache[path] = length
    return length


def compute_callout(
    part_filter: int | None,
    block_no: int,
    roles_in_block: List[str],
    *,
    include_callouts: bool,
    minimal_callouts: bool,
    include_description_callouts: bool,
    description_blocks: set[Tuple[int, int]],
    seen_roles: set[str],
    prev_role: str | None,
    prev2_role: str | None,
    last_callout_type: str | None,
) -> tuple[Path | None, str | None, set[str], str | None]:
    """
    Decide which callout (if any) to play for this block.
    Returns (path, callout_type, updated_seen_roles, updated_last_callout_type).
    """
    primary_role = next((r for r in roles_in_block if r != "_NARRATOR"), None)
    is_description = part_filter is not None and (part_filter, block_no) in description_blocks

    # Description callout for narrator-only description blocks.
    if include_description_callouts and primary_role is None and is_description:
        path = CALLOUTS_DIR / "_DESCRIPTION.wav"
        if path.exists() and last_callout_type != "description":
            return path, "description", seen_roles, "description"
        if not path.exists():
            logging.warning("Description callout missing: %s", path)
        return None, last_callout_type, seen_roles, last_callout_type

    # Role callout.
    if include_callouts and primary_role:
        need_callout = True
        if minimal_callouts and primary_role in seen_roles:
            if primary_role == prev_role:
                need_callout = False
            elif prev2_role == primary_role and prev_role and prev_role != primary_role:
                need_callout = False
        if need_callout:
            seen_roles = set(seen_roles)
            seen_roles.add(primary_role)
            path = CALLOUTS_DIR / f"{primary_role}_callout.wav"
            if path.exists():
                return path, "role", seen_roles, "role"
            logging.warning("Callout missing for role %s: %s", primary_role, path)
            return None, last_callout_type, seen_roles, last_callout_type
    return None, last_callout_type, seen_roles, last_callout_type


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


def build_block_plan(
    part_filter: int | None,
    block_no: int,
    roles_in_block: List[str],
    *,
    callout_path: Path | None,
    prev_role: str | None,
    prev2_role: str | None,
    is_last_block: bool,
    spacing_ms: int,
    callout_spacing_ms: int,
    length_cache: Dict[Path, int],
    base_offset_ms: int,
    plan_items: AudioPlan[PlanItem],
) -> tuple[List[PlanItem], str | None, str | None]:
    """Build plan items for a single block, including optional callouts."""
    start_idx = len(plan_items)
    primary_role = next((r for r in roles_in_block if r != "_NARRATOR"), None)
    current_offset = base_offset_ms

    if callout_path:
        callout_id = primary_role or "_NARRATOR"
        length_ms = get_audio_length_ms(callout_path, length_cache)
        plan_items.addClip(
            CalloutClip(path=callout_path, text="", role="_NARRATOR", clip_id=callout_id, length_ms=length_ms, offset_ms=0),
            following_silence_ms=callout_spacing_ms,
        )
        current_offset += length_ms + callout_spacing_ms

    block_segments: List[Tuple[str, str, str]] = []
    source_role = primary_role or roles_in_block[0]
    bullets = read_block_bullets(source_role, part_filter, block_no)
    for idx, text in enumerate(bullets, start=1):
        owner = "_NARRATOR" if primary_role is not None and text.startswith("(_") else (primary_role or "_NARRATOR")
        sid = f"{'' if part_filter is None else part_filter}:{block_no}:{idx}"
        block_segments.append((owner, sid, text))

    for seg_idx, (role, seg_id, text) in enumerate(block_segments):
        wav_path = SEGMENTS_DIR / role / f"{seg_id.replace(':', '_')}.wav"
        if not wav_path.exists():
            logging.error("Missing snippet %s for role %s", seg_id, role)
            continue
        length_ms = get_audio_length_ms(wav_path, length_cache)
        is_last_seg = seg_idx == len(block_segments) - 1
        gap = spacing_ms if spacing_ms > 0 and not (is_last_block and is_last_seg) else 0
        plan_items.addClip(
            SegmentClip(path=wav_path, text=text, role=role, clip_id=seg_id, length_ms=length_ms, offset_ms=0),
            following_silence_ms=gap,
        )
        current_offset += length_ms + gap
        if role != "_NARRATOR":
            prev2_role, prev_role = prev_role, role

    return list(plan_items[start_idx:]), prev_role, prev2_role


def extract_blocks(entries: List[IndexEntry], part_filter: int | None) -> List[Tuple[int, List[str]]]:
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


def build_part_plan(
    part_filter: int | None,
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
    include_description_callouts: bool = True,
    base_offset_ms: int = 0,
    chapters: List[Chapter] | None = None,
) -> tuple[AudioPlan[PlanItem], int]:
    """Build plan items for a given part (or None for preamble)."""
    entries = parse_index()
    description_blocks = description_block_keys()
    chapter_map = {c.block_id: c for c in (chapters or [])}
    inserted_chapters: set[str] = set()
    length_cache: Dict[Path, int] = {}

    block_entries = extract_blocks(entries, part_filter)

    prev_role: str | None = None
    prev2_role: str | None = None
    seen_roles: set[str] = set()
    last_callout_type: str | None = None
    audio_plan: AudioPlan = AudioPlan()
    # AudioPlan duration tracks offsets; no separate counter needed.

    for b_idx, (block_no, roles_in_block) in enumerate(block_entries):
        callout_path, _callout_type, seen_roles, last_callout_type = compute_callout(
            part_filter,
            block_no,
            roles_in_block,
            include_callouts=include_callouts,
            minimal_callouts=minimal_callouts,
            include_description_callouts=include_description_callouts,
            description_blocks=description_blocks,
            seen_roles=seen_roles,
            prev_role=prev_role,
            prev2_role=prev2_role,
            last_callout_type=last_callout_type,
        )

        block_items, prev_role, prev2_role = build_block_plan(
            part_filter,
            block_no,
            roles_in_block,
            callout_path=callout_path,
            prev_role=prev_role,
            prev2_role=prev2_role,
            is_last_block=b_idx == len(block_entries) - 1,
            spacing_ms=spacing_ms,
            callout_spacing_ms=callout_spacing_ms,
            length_cache=length_cache,
            base_offset_ms=audio_plan.duration_ms,
            plan_items=audio_plan,
        )
        for item in block_items:
            if isinstance(item, (CalloutClip, SegmentClip)) and item.clip_id:
                block_id = ":".join(item.clip_id.split(":")[:2])
                if block_id in chapter_map and block_id not in inserted_chapters:
                    chapter_template = chapter_map[block_id]
                    chapter_obj = Chapter(
                        block_id=chapter_template.block_id,
                        title=chapter_template.title,
                        offset_ms=item.offset_ms,
                    )
                    audio_plan.addChapter(chapter_obj)
                    inserted_chapters.add(block_id)

    return audio_plan, audio_plan.duration_ms


def write_plan(plan: AudioPlan[PlanItem], path: Path) -> None:
    """Persist plan items to a text file for inspection."""
    lines: List[str] = []
    for item in plan:
        mins = item.offset_ms // 60000
        secs_ms = item.offset_ms % 60000
        prefix = f"{mins:02d}:{secs_ms/1000:06.3f} "
        if isinstance(item, (CalloutClip, SegmentClip, Silence)):
            lines.append(prefix + str(item))
        elif isinstance(item, Chapter):
            suffix = f" {item.title}" if item.title else ""
            lines.append(f"{prefix}[chapter]{suffix}")
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def build_audio_plan(
    parts: List[int | None],
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
    include_description_callouts: bool = True,
    part_chapters: bool = False,
    part_gap_ms: int = 0,
    librivox: bool = False,
    part_index_offset: int = 0,
    total_parts: int | None = None,
) -> tuple[AudioPlan[PlanItem], int]:
    chapters = ChapterBuilder().build()
    plan: AudioPlan[PlanItem] = AudioPlan()
    total_count = total_parts if total_parts is not None else len(parts)
    plan.addSilence(1000)
    for idx, part in enumerate(parts):
        global_idx = part_index_offset + idx
        if librivox and global_idx == 0:
            from paths import RECORDINGS_DIR
            prologue = RECORDINGS_DIR / "_LIBRIVOX_PROLOGUE.wav"
            if prologue.exists():
                plen = len(AudioSegment.from_file(prologue))
                plan.addClip(
                    CalloutClip(
                        path=prologue,
                        text="",
                        role="_NARRATOR",
                        clip_id="_LIBRIVOX_PROLOGUE",
                        length_ms=plen,
                        offset_ms=plan.duration_ms,
                    ),
                    following_silence_ms=1000,
                )
        seg_plan, _ = build_part_plan(
            part_filter=part,
            spacing_ms=spacing_ms,
            include_callouts=include_callouts,
            callout_spacing_ms=callout_spacing_ms,
            minimal_callouts=minimal_callouts,
            include_description_callouts=include_description_callouts,
            base_offset_ms=plan.duration_ms,
            chapters=chapters,
        )

        # Append part items sequentially to the main plan, optionally inserting Librivox "part of" suffix.
        part_of_suffix_inserted = False
        part_of_suffix_path = None
        part_of_suffix_len = 0
        if librivox and global_idx > 0:
            from paths import RECORDINGS_DIR

            part_of_suffix_path = RECORDINGS_DIR / "_LIBRIVOX_EACH_PART.wav"
            part_of_suffix_len = len(AudioSegment.from_file(part_of_suffix_path))

        for item in seg_plan:
            if isinstance(item, Chapter):
                item.offset_ms = plan.duration_ms
                plan.addChapter(item)
                continue
            if isinstance(item, Silence):
                plan.addSilence(item.length_ms)
            elif isinstance(item, (CalloutClip, SegmentClip)):
                plan.addClip(
                    item.__class__(
                        path=item.path,
                        text=item.text,
                        role=item.role,
                        clip_id=item.clip_id,
                        length_ms=item.length_ms,
                        offset_ms=plan.duration_ms,
                    )
                )
                if part_of_suffix_path and not part_of_suffix_inserted:
                    # Insert part-of suffix after the first audio item.
                    plan.addSilence(INTER_WORD_PAUSE_MS)
                    plan.addClip(
                        CalloutClip(
                            path=part_of_suffix_path,
                            text="of [title] by [author]. This is a Librivox recording. All Librivox recordings are in the public domain. For more information, or to volunteer, please visit librivox.org.",
                            role="_NARRATOR",
                            clip_id="_LIBRIVOX_EACH_PART",
                            length_ms=part_of_suffix_len,
                            offset_ms=plan.duration_ms,
                        ),
                    )
                    part_of_suffix_inserted = True
            else:
                raise RuntimeError(f"Unexpected plan item type: {type(item)}")

        if part_gap_ms and idx < len(parts) - 1:
            plan.addSilence(part_gap_ms)

        if librivox:
            from paths import RECORDINGS_DIR
            endof_path = RECORDINGS_DIR / "_LIBRIVOX_ENDOF.wav"
            epilogue = RECORDINGS_DIR / "_LIBRIVOX_EPILOG.wav"
            # Use the first clip of the part as the title if no dedicated title clip.
            title_audio = RECORDINGS_DIR / f"_TITLE_PART_{part}.wav" if part is not None else None
            title_text = ""
            if title_audio and title_audio.exists():
                pass
            else:
                # Derive from first segment of the part.
                first_seg = f"{'' if part is None else part}_0_1.wav"
                title_audio = SEGMENTS_DIR / "_NARRATOR" / first_seg
                # Lookup text from narrator block if available.
                first_texts = read_block_bullets("_NARRATOR", part, 0)
                title_text = first_texts[0]
            if endof_path.exists():
                length_ms = len(AudioSegment.from_file(endof_path))
                plan.addSilence(1000)
                plan.addClip(
                    CalloutClip(
                        path=endof_path,
                        text="",
                        role="_NARRATOR",
                        clip_id="_LIBRIVOX_ENDOF",
                        length_ms=length_ms,
                        offset_ms=plan.duration_ms,
                    )
                )
            plan.addSilence(INTER_WORD_PAUSE_MS)
            if title_audio and title_audio.exists():
                tlen = len(AudioSegment.from_file(title_audio))
                clip_id = f"_TITLE_PART_{part}" if title_text == "" else f"{part}:0:1"
                plan.addClip(
                    SegmentClip(
                        path=title_audio,
                        text=title_text,
                        role="_NARRATOR",
                        clip_id=clip_id,
                        length_ms=tlen,
                        offset_ms=plan.duration_ms,
                    )
                )
            if epilogue.exists() and part is not None and global_idx == total_count - 1:
                elen = len(AudioSegment.from_file(epilogue))
                # Post-title gap
                plan.addSilence(1000)
                plan.addClip(
                    CalloutClip(
                        path=epilogue,
                        text="",
                        role="_NARRATOR",
                        clip_id="_LIBRIVOX_EPILOG",
                        length_ms=elen,
                        offset_ms=plan.duration_ms,
                    )
                )
    plan.addSilence(1000)
    return plan, plan.duration_ms


def list_parts() -> List[int | None]:
    parts: List[int | None] = []
    for p, _, _ in parse_index():
        if p not in parts:
            parts.append(p)
    parts_sorted = sorted([x for x in parts if x is not None])
    if None in parts:
        return [None] + parts_sorted
    return parts_sorted


def load_part_titles() -> Dict[int, str]:
    titles: Dict[int, str] = {}
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
        title = f"{part}_{titles.get(part, 'part')}"
    return AUDIO_PLAY_DIR / f"{title}.{audio_format}"
