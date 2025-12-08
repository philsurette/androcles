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
    NoCalloutDirector,
)
from play_text import PlayText, Block, MetaBlock
from chapter_builder import Chapter
from clip import SegmentClip, CalloutClip, SegmentClip, Silence
from audio_plan import AudioPlan, PlanItem
import paths
from spacing import (
  WORD_PAUSE_MS, 
  BLOCK_PAUSE_MS, 
  COMMA_PAUSE_MS, 
  PARAGRAPH_PAUSE_MS,
  CALLOUT_SPACING_MS,
  SEGMENT_SPACING_MS
)

LEADING_SILENCE_MS = 500
TRAILING_SILENCE_MS = 1000
LIBRIVOX_LEADING_SILENCE_MS = 1000
LIBRIVOX_TRAILING_SILENCE_MS = 5000

IndexEntry = Tuple[int | None, int, str]

@dataclass
class PlayPlanBuilder:
    """Encapsulates play context and helpers for building audio plans."""

    play: PlayText
    director: CalloutDirector | None = None
    chapters: List[Chapter] | None = None
    segment_spacing_ms: int = SEGMENT_SPACING_MS
    include_callouts: bool = False
    callout_spacing_ms: int = CALLOUT_SPACING_MS
    minimal_callouts: bool = False
    part_gap_ms: int = 0
    librivox: bool = False
    length_cache: Dict[Path, int] = field(default_factory=dict)
    audio_plan: AudioPlan = field(init=False)

    def __post_init__(self) -> None:
        if self.director is None:
            self.director = NoCalloutDirector(self.play)
        if self.chapters is None:
            self.chapters = []
        self.plan = AudioPlan() 

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
            gap = self.segment_spacing_ms if self.segment_spacing_ms > 0 and not (is_last_block and is_last_seg) else 0
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
    
    def _add_clip(self, 
            folder: Path, 
            file_name: str, 
            text: str, 
            following_silence_ms: int = 0,
            ) -> None:
        path = folder / f"{file_name}.wav"
        self.plan.addClip(
            SegmentClip(
                path=path,
                text=text,
                role=None,
                clip_id=None,
                length_ms=self.get_audio_length_ms(path, self.length_cache),
            ),
            following_silence_ms
        )

    def _add_snippet(self,
            file_name: str, 
            text: str = None, 
            following_silence_ms: int = 0,
        ) -> None:
        if text is None:
            text = file_name
        self._add_clip(
            file_name=file_name,
            text=text,
            following_silence_ms=following_silence_ms,
            folder=paths.GENERAL_SNIPPETS_DIR
        )

    def _add_words(self,
            file_name: str, 
            text: str = None, 
            sentence_start = False,
            sentence_end = False,
            phrase_end = False,
            following_silence_ms: int = None,
            folder: Path = paths.GENERAL_SNIPPETS_DIR
        ) -> None:
        if text is None:
            text = file_name
            if sentence_start is True:
                text = text.capitalize()
            if sentence_end is True:
                text = f"{text}."
            elif phrase_end is True:
                text = f"{text},"
        if following_silence_ms is None:
            if sentence_end is True:
                following_silence_ms = BLOCK_PAUSE_MS
            elif phrase_end is True:
                following_silence_ms = COMMA_PAUSE_MS
            else:
                following_silence_ms = WORD_PAUSE_MS
        self._add_clip(
            file_name=file_name,
            text=text,
            following_silence_ms=following_silence_ms,
            folder=folder
        )

    def _add_sentence(self,
            file_name: str, 
            text: str = None, 
            following_silence_ms: int = BLOCK_PAUSE_MS,
            folder: Path = paths.GENERAL_SNIPPETS_DIR
        ) -> None:
        if text is None:
            text = f"{file_name.capitalize()}."
        self._add_clip(
            file_name=file_name,
            text=text,
            following_silence_ms=following_silence_ms,
            folder=folder
        )

    def _add_librivox_start_of_recording(self, part_id: int) -> None:
        if not self.librivox:
            return
        if self.play.first_part_id == part_id:
            self._add_words(f'section {part_id} of', sentence_start=True)
            self._add_recording(
                file_name="_TITLE",
                text=f"""{self.play.title}. """,
                silence_ms=BLOCK_PAUSE_MS,
            )
            self._add_sentence(
                "this is a LibriVox recording",
                folder=paths.LIBRIVOX_SNIPPETS_DIR
            )
            self._add_sentence(
                "all LibriVox recordings are in the public domain",
                folder=paths.LIBRIVOX_SNIPPETS_DIR
            )
            self._add_words(
                "for more information or to volunteer",
                sentence_start=True,
                phrase_end=True,
                folder=paths.LIBRIVOX_SNIPPETS_DIR
            )
            self._add_words(
                "please visit librivox dot org",
                sentence_end=True,
                folder=paths.LIBRIVOX_SNIPPETS_DIR
            )
            self._add_words(
                file_name="read by",
                sentence_start=True
            )
            self._add_recording(
                file_name="_READER",
                text="Phil Surette.",
                silence_ms=BLOCK_PAUSE_MS
            )
            self._add_title_by_author()
        
    def _add_recording(self, 
                           file_name: str, 
                           text: str, 
                           silence_ms: int) -> None:
        self._add_clip(
            folder=paths.RECORDINGS_DIR,
            file_name=file_name,
            text=text,
            following_silence_ms=silence_ms      
        )

    def _add_title_by_author(self):
        self._add_recording(
            file_name="_TITLE",
            text=f"{self.play.title},",
            silence_ms=COMMA_PAUSE_MS
        )
        self._add_words(
            file_name="by",
        )
        self._add_recording(
            file_name="_AUTHOR",
            text=f"{self.play.author}.",
            silence_ms=BLOCK_PAUSE_MS
        )        

    def _add_librivox_start_of_section(self, part_id: int) -> None:
        if not self.librivox:
            return
        if self.play.first_part_id == part_id:
            return
        self._add_words(f"section {part_id} of", sentence_start=True)
        self._add_title_by_author()
        self._add_sentence(
            "this librivox recording is in the public domain",
            folder=paths.LIBRIVOX_SNIPPETS_DIR
        )
    
    def _add_librivox_end_of_section(self, part_no: int) -> None:
        if not self.librivox:
            return
        self.plan.add_silence(PARAGRAPH_PAUSE_MS)
        self._add_sentence(f"end of section {part_no}")

    def _add_librivox_end_of_recording(self, part_id: int) -> None:
        if not self.librivox:
            return
        if self.play.last_part_id == part_id: 
            self._add_words("end of", sentence_start=True)
            self._add_title_by_author()
    
    def _add_leading_silence(self) -> None:
        if self.librivox:
            self.plan.add_silence(LIBRIVOX_LEADING_SILENCE_MS)
        else:
            self.plan.add_silence(LEADING_SILENCE_MS)

    def _add_trailing_silence(self) -> None:
        if self.librivox:
            self.plan.add_silence(LIBRIVOX_TRAILING_SILENCE_MS)
        else:
            self.plan.add_silence(TRAILING_SILENCE_MS)
            
    def build_audio_plan(
        self,
        part_no: int = None
    ) -> AudioPlan:
        self._add_leading_silence()
        parts = [self.play.getPart(part_no)] if part_no != None else [p for p in self.play.parts]
        for part in parts:
            part_id = part.part_no
            self._add_librivox_start_of_recording(part_id=part_id)
            self._add_librivox_start_of_section(part_id=part_id)

            seg_plan, _ = self.build_part_plan(part_filter=part.part_no)

            ## add segments to plan
            for item in seg_plan:
                if isinstance(item, Chapter):
                    item.offset_ms = self.plan.duration_ms
                    self.plan.addChapter(item)
                    continue
                if isinstance(item, Silence):
                    self.plan.add_silence(item.length_ms)
                elif isinstance(item, (CalloutClip, SegmentClip)):
                    self.plan.addClip(
                        item.__class__(
                            path=item.path,
                            text=item.text,
                            role=item.role,
                            clip_id=item.clip_id,
                            length_ms=item.length_ms,
                            offset_ms=self.plan.duration_ms,
                        )
                    )
                else:
                    raise RuntimeError(f"Unexpected plan item type: {type(item)}")

            ## add end of part clips
            self.plan.add_silence(PARAGRAPH_PAUSE_MS)
            if self.librivox:
                self._add_librivox_end_of_section(part_no=part_id)
                self._add_librivox_end_of_recording(part_id=part_id)
            self._add_trailing_silence()

        return self.plan

    @staticmethod
    def load_audio_by_path(path: Path, cache: Dict[Path, AudioSegment | None]) -> AudioSegment | None:
        """Load audio by path with caching."""
        if path in cache:
            return cache[path]
        if not path.exists():
            raise RuntimeError("Audio file missing: %s", path)
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


def write_plan(plan: AudioPlan, path: Path) -> None:
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





