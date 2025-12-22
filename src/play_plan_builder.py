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
from play import Play, Block, MetaBlock
from segment import SimultaneousSegment
from chapter_builder import Chapter
from clip import SegmentClip, CalloutClip, Silence, ParallelClips
from audio_plan import AudioPlan, PlanItem
import paths
from play_plan_decorator import PlayPlanDecorator, DefaultPlayPlanDecorator, LibrivoxPlayPlanDecorator
from spacing import (
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
class BlockBullet:
    """Represents a block segment ready for planning."""

    segment_no: int
    owners: List[str]
    text: str
    simultaneous: bool = False

@dataclass
class PlayPlanBuilder:
    """Encapsulates play context and helpers for building audio plans."""

    play: Play
    director: CalloutDirector | None = None
    chapters: List[Chapter] | None = None
    play_plan_decorator: PlayPlanDecorator | None = None
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
        if self.play_plan_decorator is None:
            if self.librivox:
                self.play_plan_decorator = LibrivoxPlayPlanDecorator(
                    play = self.play, 
                    plan = self.plan
                )
            else:
                self.play_plan_decorator = DefaultPlayPlanDecorator(
                    play = self.play, 
                    plan = self.plan
                )

    def list_parts(self) -> List[int | None]:
        parts: List[int | None] = []
        for blk in self.play.blocks:
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

        bullets = self.read_block_bullets(block)
        for b_idx, bullet in enumerate(bullets):
            seg_id = f"{'' if block_id.part_id is None else block_id.part_id}:{block_id.block_no}:{bullet.segment_no}"
            is_last_seg = b_idx == len(bullets) - 1
            gap = self.segment_spacing_ms if self.segment_spacing_ms > 0 and not (is_last_block and is_last_seg) else 0
            if bullet.simultaneous or len(bullet.owners) > 1:
                clips: List[SegmentClip] = []
                for role in bullet.owners:
                    wav_path = paths.SEGMENTS_DIR / role / f"{seg_id.replace(':', '_')}.wav"
                    if not wav_path.exists():
                        logging.error("Missing snippet %s for role %s", seg_id, role)
                        length_ms = 0
                    else:
                        length_ms = self.get_audio_length_ms(wav_path, self.length_cache)
                    clips.append(
                        SegmentClip(
                            path=wav_path,
                            text=bullet.text,
                            role=role,
                            clip_id=seg_id,
                            length_ms=length_ms,
                            offset_ms=0,
                        )
                    )
                plan_items.add_parallel(clips, following_silence_ms=gap)
            else:
                role = bullet.owners[0]
                wav_path = paths.SEGMENTS_DIR / role / f"{seg_id.replace(':', '_')}.wav"
                if not wav_path.exists():
                    logging.error("Missing snippet %s for role %s", seg_id, role)
                    length_ms = 0
                else:
                    length_ms = self.get_audio_length_ms(wav_path, self.length_cache)
                plan_items.addClip(
                    SegmentClip(path=wav_path, text=bullet.text, role=role, clip_id=seg_id, length_ms=length_ms, offset_ms=0),
                    following_silence_ms=gap,
                )

        return list(plan_items[start_idx:])

    def build_part_plan(
        self,
        part_filter: int | None,
        chapters: List[Chapter] | None = None,
        director: CalloutDirector | None = None,
    ) -> AudioPlan:
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
                elif isinstance(item, ParallelClips):
                    for clip in item.clips:
                        if not getattr(clip, "clip_id", None):
                            continue
                        block_id = ":".join(str(clip.clip_id).split(":")[:2])
                        if block_id in chapter_map and block_id not in inserted_chapters:
                            chapter_template = chapter_map[block_id]
                            chapter_obj = Chapter(
                                block_id=chapter_template.block_id,
                                title=chapter_template.title,
                                offset_ms=item.offset_ms,
                            )
                            audio_plan.addChapter(chapter_obj)
                            inserted_chapters.add(block_id)

        return audio_plan
            
    def build_audio_plan(
        self,
        part_no: int = None
    ) -> AudioPlan:
        parts = [self.play.getPart(part_no)] if part_no != None else [p for p in self.play.parts]
        for part in parts:
            part_id = part.part_no
            if part_id == self.play.first_part_id:
                self.play_plan_decorator.add_project_preamble(part_no=part_id)
            else:                
                self.play_plan_decorator.add_section_preamble(part_no=part_id)

            seg_plan = self.build_part_plan(part_filter=part.part_no)

            ## add segments to plan
            for item in seg_plan:
                if isinstance(item, Chapter):
                    item.offset_ms = self.plan.duration_ms
                    self.plan.addChapter(item)
                    continue
                if isinstance(item, Silence):
                    self.plan.add_silence(item.length_ms)
                elif isinstance(item, ParallelClips):
                    clips: List[SegmentClip] = []
                    for clip in item.clips:
                        clips.append(
                            clip.__class__(
                                path=clip.path,
                                text=clip.text,
                                role=clip.role,
                                clip_id=clip.clip_id,
                                length_ms=clip.length_ms,
                                offset_ms=self.plan.duration_ms,
                            )
                        )
                    self.plan.add_parallel(clips, following_silence_ms=0)
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
            if self.play.last_part_id == part_id: 
                self.play_plan_decorator.add_project_epilog(part_no=part_id)
            else:
                self.play_plan_decorator.add_section_epilog(part_no=part_id)

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

    def read_block_bullets(self, block_obj: Block) -> List[BlockBullet]:
        """
        Return BlockBullet entries for the given block from in-memory PlayText.
        Owner is derived from the segment role or block owner for directions/meta.
        """
        blk = block_obj
        if not blk or not hasattr(blk, "segments"):
            logging.warning("Block %s not found in play text", getattr(blk, "block_id", None))
            return []
        bullets: List[BlockBullet] = []
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
                prev = bullets[-1]
                bullets[-1] = BlockBullet(
                    segment_no=prev.segment_no,
                    owners=prev.owners,
                    text=prev.text + text,
                    simultaneous=prev.simultaneous,
                )
                continue

            if isinstance(seg, SimultaneousSegment):
                owners = list(getattr(seg, "roles", [])) or []
                if not owners:
                    owners = [getattr(blk, "role", "_NARRATOR")]
                bullets.append(
                    BlockBullet(
                        segment_no=seg.segment_id.segment_no,
                        owners=owners,
                        text=text,
                        simultaneous=True,
                    )
                )
                continue

            owner = None
            if hasattr(seg, "role"):
                owner = getattr(seg, "role", None)
            if not owner:
                owner = "_NARRATOR"
            bullets.append(
                BlockBullet(
                    segment_no=seg.segment_id.segment_no,
                    owners=[owner],
                    text=text,
                )
            )
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
        elif isinstance(item, ParallelClips):
            for clip in item.clips:
                lines.append(prefix + f"[parallel] {clip}")
        elif isinstance(item, Chapter):
            suffix = f" {item.title}" if item.title else ""
            lines.append(f"{prefix}[chapter]{suffix}")
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")
