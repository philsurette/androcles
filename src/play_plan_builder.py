#!/usr/bin/env python3
"""Build audio plans for the play."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import logging
import re
from typing import Dict, List, Tuple, Union

from pydub import AudioSegment

from callout_director import (
    CalloutDirector,
    ConversationAwareCalloutDirector,
    NoCalloutDirector,
    RoleCalloutDirector,
)
from play_text import PlayText, PlayTextParser, Block
from narrator_splitter import parse_narrator_blocks
from chapter_builder import Chapter, ChapterBuilder
from clip import SegmentClip, CalloutClip, SegmentClip, Silence
from audio_plan import AudioPlan, PlanItem
from paths import (
    BLOCKS_DIR,
    BLOCKS_EXT,
    AUDIO_PLAY_DIR,
    PARAGRAPHS_PATH,
    SEGMENTS_DIR
)


IndexEntry = Tuple[int | None, int, str]
BlockMap = Dict[Tuple[int | None, int], List[str]]

INTER_WORD_PAUSE_MS = 300

def parse_index(play_text: PlayText | None = None) -> List[IndexEntry]:
    """Return ordered (part, block, role) tuples derived from PlayText, mirroring INDEX.files."""
    play = play_text or PlayTextParser().parse()
    return play.to_index_entries()

def load_segment_maps(play_text: PlayText | None = None) -> Dict[str, BlockMap]:
    """Build segment-id maps for all roles present in the play."""
    play = play_text or PlayTextParser().parse()
    return play.build_segment_maps()


@dataclass
class PlayPlanBuilder:
    """Encapsulates play context and helpers for building audio plans."""

    play_text: PlayText
    director: CalloutDirector | None = None
    chapters: List[Chapter] | None = None
    spacing_ms: int = 0
    include_callouts: bool = False
    callout_spacing_ms: int = 300
    part_gap_ms: int = 0
    librivox: bool = False
    length_cache: Dict[Path, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.director is None:
            self.director = NoCalloutDirector(self.play_text)
        if self.chapters is None:
            self.chapters = []

    def parse_index(self) -> List[IndexEntry]:
        return parse_index(self.play_text)

    def list_parts(self) -> List[int | None]:
        parts: List[int | None] = []
        for blk in self.play_text:
            pid = blk.block_id.part_id
            if pid not in parts:
                parts.append(pid)
        parts_sorted = sorted([x for x in parts if x is not None])
        if None in parts:
            return [None] + parts_sorted
        return parts_sorted

    def load_segment_maps(self) -> Dict[str, BlockMap]:
        return self.play_text.build_segment_maps()

    def build_block_plan(
        self,
        block: Block,
        *,
        callout_clip: CalloutClip | None,
        is_last_block: bool,
        plan_items: AudioPlan[PlanItem],
    ) -> List[PlanItem]:
        """Build plan items for a single block, including optional callouts."""
        start_idx = len(plan_items)
        block_id = block.block_id
        if callout_clip:
            plan_items.addClip(callout_clip, following_silence_ms=self.callout_spacing_ms)
        primary_role = block.owner if block.owner != "_NARRATOR" else None

        block_segments: List[Tuple[str, str, str]] = []
        source_role = primary_role or block.roles[0]
        bullets = read_block_bullets(source_role, block_id.part_id, block_id.block_no)
        for idx, text in enumerate(bullets, start=1):
            owner = block.owner_for_text(text) or "_NARRATOR"
            sid = f"{'' if block_id.part_id is None else block_id.part_id}:{block_id.block_no}:{idx}"
            block_segments.append((owner, sid, text))

        for seg_idx, (role, seg_id, text) in enumerate(block_segments):
            wav_path = SEGMENTS_DIR / role / f"{seg_id.replace(':', '_')}.wav"
            if not wav_path.exists():
                logging.error("Missing snippet %s for role %s", seg_id, role)
                continue
            length_ms = get_audio_length_ms(wav_path, self.length_cache)
            is_last_seg = seg_idx == len(block_segments) - 1
            gap = self.spacing_ms if self.spacing_ms > 0 and not (is_last_block and is_last_seg) else 0
            plan_items.addClip(
                SegmentClip(path=wav_path, text=text, role=role, clip_id=seg_id, length_ms=length_ms, offset_ms=0),
                following_silence_ms=gap,
            )

        return list(plan_items[start_idx:])

    def build_part_plan(
        self,
        part_filter: int | None,
        chapters: List[Chapter] | None = None,
        director: CalloutDirector | None = None,
    ) -> tuple[AudioPlan[PlanItem], int]:
        """Build plan items for a given part (or None for preamble)."""
        entries = self.parse_index()
        chapter_map = {c.block_id: c for c in (chapters if chapters is not None else self.chapters or [])}
        inserted_chapters: set[str] = set()
        director_obj = director or self.director or NoCalloutDirector(self.play_text)

        part_obj = self.play_text.getPart(part_filter)
        if part_obj is None or not part_obj.blocks:
            raise RuntimeError(f"No segments found for part {part_filter!r}")
        part_blocks = part_obj.blocks

        audio_plan: AudioPlan = AudioPlan()

        for b_idx, block in enumerate(part_blocks):
            block_id = block.block_id
            callout_clip = director_obj.calloutForBlock(block_id) if self.include_callouts else None

            block_items = self.build_block_plan(
                block,
                callout_clip=callout_clip,
                is_last_block=b_idx == len(part_blocks) - 1,
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

    def build_audio_plan(
        self,
        parts: List[int | None],
        part_index_offset: int = 0,
        total_parts: int | None = None,
    ) -> tuple[AudioPlan[PlanItem], int]:
        plan: AudioPlan[PlanItem] = AudioPlan()
        total_count = total_parts if total_parts is not None else len(parts)
        plan.addSilence(1000)
        for idx, part in enumerate(parts):
            global_idx = part_index_offset + idx
            if self.librivox and global_idx == 0:
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
            seg_plan, _ = self.build_part_plan(part_filter=part, chapters=self.chapters, director=self.director)

            # Append part items sequentially to the main plan, optionally inserting Librivox "part of" suffix.
            part_of_suffix_inserted = False
            part_of_suffix_path = None
            part_of_suffix_len = 0
            if self.librivox and global_idx > 0:
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

            if self.part_gap_ms and idx < len(parts) - 1:
                plan.addSilence(self.part_gap_ms)

            if self.librivox:
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
                if endof_path.exists() and global_idx < total_count - 1:
                    length_ms = len(AudioSegment.from_file(endof_path))
                    plan.addSilence(2000)
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
                    plan.addSilence(2000)
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
    callout_clip: CalloutClip | None,
    is_last_block: bool,
    spacing_ms: int,
    callout_spacing_ms: int,
    length_cache: Dict[Path, int],
    plan_items: AudioPlan[PlanItem],
) -> List[PlanItem]:
    """Build plan items for a single block, including optional callouts."""
    start_idx = len(plan_items)
    primary_role = next((r for r in roles_in_block if r != "_NARRATOR"), None)
    if callout_clip:
        plan_items.addClip(callout_clip, following_silence_ms=callout_spacing_ms)

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
    return list(plan_items[start_idx:])


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
    chapters: List[Chapter] | None = None,
    director: CalloutDirector | None = None,
    play_text: PlayText | None = None,
) -> tuple[AudioPlan[PlanItem], int]:
    """Build plan items for a given part (or None for preamble)."""
    play = play_text or PlayTextParser().parse()
    builder = PlayPlanBuilder(
        play_text=play,
        director=director or NoCalloutDirector(play),
        chapters=chapters or [],
    )
    return builder.build_part_plan(
        part_filter=part_filter,
        chapters=chapters,
        director=director,
    )


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
    part_chapters: bool = False,
    part_gap_ms: int = 0,
    librivox: bool = False,
    part_index_offset: int = 0,
    total_parts: int | None = None,
) -> tuple[AudioPlan[PlanItem], int]:
    play = PlayTextParser().parse()
    chapters = ChapterBuilder().build()
    if include_callouts:
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(play) if minimal_callouts else RoleCalloutDirector(play)
        )
    else:
        director = NoCalloutDirector(play)
    builder = PlayPlanBuilder(
        play_text=play,
        director=director,
        chapters=chapters,
        spacing_ms=spacing_ms,
        include_callouts=include_callouts,
        callout_spacing_ms=callout_spacing_ms,
        part_gap_ms=part_gap_ms,
        librivox=librivox,
    )
    return builder.build_audio_plan(
        parts=parts,
        part_index_offset=part_index_offset,
        total_parts=total_parts,
    )


def list_parts(play_text: PlayText | None = None) -> List[int | None]:
    play = play_text or PlayTextParser().parse()
    return PlayPlanBuilder(play_text=play).list_parts()


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
