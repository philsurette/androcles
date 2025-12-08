#!/usr/bin/env python3
"""Container class for audio plans."""
from __future__ import annotations

from typing import Iterable, TypeVar, Generic, List

from clip import Clip, Silence
from chapter_builder import Chapter
from pathlib import Path

PlanItem = Clip | Chapter
PI = TypeVar("PI", bound=PlanItem)

class AudioPlan(List[PI], Generic[PI]):
    """Simple list subclass to represent an ordered audio plan."""

    def __init__(self, items: Iterable[PI] | None = None) -> None:
        super().__init__(items or [])
        self.duration_ms: int = 0

    @property
    def items(self) -> List[PlanItem]:
        return self

    def addClip(self, clip: Clip, following_silence_ms: int = 0) -> None:
        """Append a clip and optional trailing silence."""
        clip.offset_ms = self.duration_ms
        self.append(clip)
        offset_ms = clip.offset_ms + clip.length_ms
        self.duration_ms = max(self.duration_ms, offset_ms)
        if following_silence_ms > 0:
            self.append(Silence(following_silence_ms, offset_ms=offset_ms))
            offset_ms += following_silence_ms
            self.duration_ms = max(self.duration_ms, offset_ms)

    def addSilence(self, ms: int) -> None:
        """Append silence if duration > 0."""
        if ms <= 0:
            return
        offset_ms = self.duration_ms
        self.append(Silence(ms, offset_ms=offset_ms))
        offset_ms += ms
        self.duration_ms = max(self.duration_ms, offset_ms)

    def addChapter(self, chapter: Chapter) -> None:
        """Add a chapter marker (append or insert) and update duration if offset is known."""
        chapter.offset_ms = self.duration_ms
        self.append(chapter)
      
