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
from play_text import PlayText, PlayTextParser, Block, BlockId, MetaBlock
from chapter_builder import Chapter, ChapterBuilder
from clip import SegmentClip, CalloutClip, SegmentClip, Silence
from audio_plan import AudioPlan, PlanItem
import paths

IndexEntry = Tuple[int | None, int, str]

INTER_WORD_PAUSE_MS = 300
INTER_BLOCK_PAUSE_MS = 1000

@dataclass
class PlayPlanBuilder:
    """Encapsulates play context and helpers for building audio plans."""

    play: PlayText
    director: CalloutDirector | None = None
    chapters: List[Chapter] | None = None
    spacing_ms: int = 0
    include_callouts: bool = False
    callout_spacing_ms: int = 300
    minimal_callouts: bool = False
    part_gap_ms: int = 0
    librivox: bool = False
    length_cache: Dict[Path, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.director is None:
            self.director = NoCalloutDirector(self.play)
        if self.chapters is None:
            self.chapters = []

    def list_parts(self) -> List[int | None]:
        parts: List[int | None] = []
        for blk in self.play:
            pid = blk.block_id.part_id
            if pid not in parts:
                parts.append(pid)
        parts_sorted = sorted([x for x in parts if x is not None])
        if None in parts:
            return [None] + parts_sorted
        return parts_sorted

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
            # Place callout before the block with a short gap into the first line.
            plan_items.addClip(callout_clip, following_silence_ms=self.callout_spacing_ms)

        block_segments: List[Tuple[str, str, str]] = []
        bullets = self.read_block_bullets(block)
        for seg_no, owner, text in bullets:
            sid = f"{'' if block_id.part_id is None else block_id.part_id}:{block_id.block_no}:{seg_no}"
            block_segments.append((owner, sid, text))

        for seg_idx, (role, seg_id, text) in enumerate(block_segments):
            wav_path = paths.SEGMENTS_DIR / role / f"{seg_id.replace(':', '_')}.wav"
            if not wav_path.exists():
                logging.error("Missing snippet %s for role %s", seg_id, role)
                length_ms = 0
            else:
                length_ms = self.get_audio_length_ms(wav_path, self.length_cache)
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
        chapter_map = {c.block_id: c for c in (chapters if chapters is not None else self.chapters or [])}
        inserted_chapters: set[str] = set()
        director_obj = director or self.director or NoCalloutDirector(self.play)

        part_obj = self.play.getPart(part_filter)
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
    
    def _librivox_prologue(self) -> CalloutClip:
        prologue_path = paths.RECORDINGS_DIR / "_LIBRIVOX_PROLOGUE.wav"
        length_ms = self.get_audio_length_ms(prologue_path, self.length_cache)
        return SegmentClip(
            path=prologue_path,
            text="Prologue of Androcles and the Lion. This is a LibriVox recording. All LibriVox recordings are in the public domain. For more information or to volunteer, please visit librivox.org. Read by Phil Surette.",
            role="_NARRATOR",
            clip_id="_LIBRIVOX_PROLOGUE",
            length_ms=length_ms,
            offset_ms=0,
        )

    def _librivox_title_and_author(self) -> CalloutClip:
        title_path = paths.RECORDINGS_DIR / "_LIBRIVOX_TITLE_AND_AUTHOR.wav"
        length_ms = self.get_audio_length_ms(title_path, self.length_cache)
        return SegmentClip(
            path=title_path,
            text=f"{self.play.title}, {self.play.author}.",
            role="_NARRATOR",
            clip_id="_LIBRIVOX_TITLE_AND_AUTHOR",
            length_ms=length_ms,
            offset_ms=0,
        )
    
    def _add_librivox_prologue(self, plan: AudioPlan[PlanItem], part_id: int) -> None:
        if not self.librivox:
            return
        if self.play.first_part_id == part_id:
            plan.addClip(self._librivox_prologue(), 
                         following_silence_ms=INTER_BLOCK_PAUSE_MS)
            plan.addClip(self._librivox_title_and_author(), 
                         following_silence_ms=INTER_BLOCK_PAUSE_MS)
    
    def _add_librivox_each_part_title_suffix(self, plan: AudioPlan[PlanItem], part_id: int) -> None:
        if not self.librivox:
            return
        if self.play.first_part_id == part_id:
            return
        path = paths.RECORDINGS_DIR / "_LIBRIVOX_EACH_PART.wav"
        plan.addClip(
            SegmentClip(
                path=path,
                text=f"of {self.play.title}. This LibriVox recording is in the public domain.",
                role="_NARRATOR",
                clip_id="_LIBRIVOX_EACH_PART",
                length_ms=self.get_audio_length_ms(path, self.length_cache),
                offset_ms=plan.duration_ms,
            ),
            following_silence_ms=INTER_BLOCK_PAUSE_MS,
        )
    
    def _add_librivox_endof(self, plan: AudioPlan[PlanItem], part_id: int) -> None:
        if not self.librivox:
            return
        part = self.play.getPart(part_id)
        path = paths.RECORDINGS_DIR / "_LIBRIVOX_ENDOF.wav"
        part = self.play.getPart(part_id)
        # plan.addSilence(2000)
        plan.addClip(
            SegmentClip(
                path=path,
                text=f"End of",
                role="_NARRATOR",
                clip_id="_LIBRIVOX_ENDOF",
                length_ms=self.get_audio_length_ms(path, self.length_cache),
                offset_ms=plan.duration_ms,
            ),
            following_silence_ms=INTER_WORD_PAUSE_MS,
        )
        path = paths.SEGMENTS_DIR / "_NARRATOR" / f"{part_id}_0_1.wav"
        plan.addClip(
            SegmentClip(
                path=path,
                text=part.title,
                role="_NARRATOR",
                clip_id=f"{part_id}:0:1",
                length_ms=self.get_audio_length_ms(path, self.length_cache),
                offset_ms=plan.duration_ms,
            ),
            following_silence_ms=INTER_BLOCK_PAUSE_MS,
        )

    def _add_librivox_epilogue(self, plan: AudioPlan[PlanItem], part_id: int) -> None:
        if not self.librivox:
            return
        part = self.play.getPart(part_id)
        if self.play.last_part_id == part_id:            
            path = paths.RECORDINGS_DIR / "_LIBRIVOX_EPILOG.wav"
            # plan.addSilence(2000)
            plan.addClip(
                SegmentClip(
                    path=path,
                    text="Epilogue. You have been listening to a LibriVox recording. All LibriVox recordings are in the public domain. For more information or to volunteer, please visit librivox.org. Read by Phil Surette.",
                    role="_NARRATOR",
                    clip_id="_LIBRIVOX_EPILOG",
                    length_ms=self.get_audio_length_ms(path, self.length_cache),
                    offset_ms=plan.duration_ms,
                ),
                following_silence_ms=INTER_BLOCK_PAUSE_MS,
            )
    
    def _add_librivox_trailing_silence(self, plan: AudioPlan) -> None:
        plan.addSilence(3000)
            
    def build_audio_plan(
        self,
        parts: List[int | None],
        part_index_offset: int = 0,
        total_parts: int | None = None,
    ) -> tuple[AudioPlan[PlanItem], int]:
        plan: AudioPlan[PlanItem] = AudioPlan()
        plan.addSilence(1000)
        for idx, part in enumerate(parts):
            part_id = part_index_offset + idx
            self._add_librivox_prologue(plan=plan, part_id=part_id)

            seg_plan, _ = self.build_part_plan(part_filter=part)

            ## add segments to plan
            for item in seg_plan:
                if isinstance(item, Chapter):
                    item.offset_ms = plan.duration_ms
                    plan.addChapter(item)
                    self._add_librivox_each_part_title_suffix(plan=plan, part_id=part_id)
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
                else:
                    raise RuntimeError(f"Unexpected plan item type: {type(item)}")

            if self.part_gap_ms and idx < len(parts) - 1:
                plan.addSilence(self.part_gap_ms)

            ## add end of part clips
            self._add_librivox_endof(plan=plan, part_id=part_id)
            self._add_librivox_epilogue(plan=plan, part_id=part_id)
            plan.addSilence(1000)
            self._add_librivox_trailing_silence(plan=plan)

        return plan, plan.duration_ms

    @staticmethod
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

    @staticmethod
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

    def read_block_bullets(self, block_obj: Block) -> List[Tuple[int, str, str]]:
        """
        Return tuples of (segment_no, owner, text) for the given block from in-memory PlayText.
        Owner is derived from the segment role or block owner for directions/meta.
        """
        blk = block_obj
        if not blk or not hasattr(blk, "segments"):
            logging.warning("Block %s not found in play text", getattr(blk, "block_id", None))
            return []
        bullets: List[Tuple[int, str, str]] = []
        for seg in getattr(blk, "segments", []):
            text = getattr(seg, "text", "").strip()
            if not text:
                continue
            # Strip heading markers from meta headings for friendlier titles.
            if isinstance(blk, MetaBlock) and text.startswith("##") and text.endswith("##"):
                cleaned = text.strip("# ").strip()
                m = re.match(r"^\s*\d+\s*[:.]\s*(.*)$", cleaned)
                text = m.group(1).strip() if m else cleaned
            # Merge standalone trivial punctuation into previous text.
            if text in {".", ",", ":", ";"} and bullets:
                prev_no, prev_owner, prev_text = bullets[-1]
                bullets[-1] = (prev_no, prev_owner, prev_text + text)
                continue
            owner = blk.owner_for_text(text) if hasattr(blk, "owner_for_text") else (getattr(seg, "role", None) or getattr(blk, "owner", "_NARRATOR"))
            bullets.append((seg.segment_id.segment_no, owner or "_NARRATOR", text))
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
    bullets = PlayPlanBuilder.read_block_bullets(source_role, part_filter, block_no)
    for idx, text in enumerate(bullets, start=1):
        owner = "_NARRATOR" if primary_role is not None and text.startswith("(_") else (primary_role or "_NARRATOR")
        sid = f"{'' if part_filter is None else part_filter}:{block_no}:{idx}"
        block_segments.append((owner, sid, text))

    for seg_idx, (role, seg_id, text) in enumerate(block_segments):
        wav_path = paths.SEGMENTS_DIR / role / f"{seg_id.replace(':', '_')}.wav"
        if not wav_path.exists():
            logging.error("Missing snippet %s for role %s", seg_id, role)
            continue
        length_ms = PlayPlanBuilder.get_audio_length_ms(wav_path, length_cache)
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
        play=play,
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
        play=play,
        director=director,
        chapters=chapters,
        spacing_ms=spacing_ms,
        include_callouts=include_callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
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
    return PlayPlanBuilder(play=play).list_parts()


def load_part_titles() -> Dict[int, str]:
    titles: Dict[int, str] = {}
    heading_re = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
    for line in paths.PARAGRAPHS_PATH.read_text(encoding="utf-8-sig").splitlines():
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
    return paths.AUDIO_PLAY_DIR / f"{title}.{audio_format}"
