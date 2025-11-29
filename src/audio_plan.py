#!/usr/bin/env python3
"""Container class for audio plans."""
from __future__ import annotations

from typing import Iterable, TypeVar, Generic, List

from clip import Clip, Silence
from chapter_builder import Chapter

PlanItem = Clip | Chapter
T = TypeVar("T", bound=PlanItem)


class AudioPlan(List[T], Generic[T]):
    """Simple list subclass to represent an ordered audio plan."""

    def __init__(self, items: Iterable[T] | None = None) -> None:
        super().__init__(items or [])
        self.duration_ms: int = 0

    def addClip(self, clip: Clip, following_silence_ms: int = 0) -> None:
        """Append a clip and optional trailing silence."""
        self.append(clip)
        offset_ms = clip.offset_ms + clip.length_ms
        self.duration_ms = max(self.duration_ms, offset_ms)
        if following_silence_ms > 0:
            self.append(Silence(following_silence_ms, offset_ms=offset_ms))
            offset_ms += following_silence_ms
            self.duration_ms = max(self.duration_ms, offset_ms)

    def addSilence(self, ms: int, offset_ms: int = 0) -> None:
        """Append silence if duration > 0."""
        if ms <= 0:
            return
        self.append(Silence(ms, offset_ms=offset_ms))
        offset_ms += ms
        self.duration_ms = max(self.duration_ms, offset_ms)

    def addChapter(self, chapter: Chapter, index: int | None = None) -> None:
        """Add a chapter marker (append or insert) and update duration if offset is known."""
        if index is None:
            self.append(chapter)
        else:
            self.insert(index, chapter)
        if chapter.offset_ms is not None:
            self.duration_ms = max(self.duration_ms, chapter.offset_ms)
