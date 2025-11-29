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

    def addClip(self, clip: Clip, following_silence_ms: int = 0) -> int:
        """Append a clip and optional trailing silence. Returns resulting offset."""
        self.append(clip)
        offset_ms = clip.offset_ms + clip.length_ms
        if following_silence_ms > 0:
            self.append(Silence(following_silence_ms, offset_ms=offset_ms))
            offset_ms += following_silence_ms
        return offset_ms

    def addSilence(self, ms: int, offset_ms: int = 0) -> int:
        """Append silence if duration > 0. Returns resulting offset."""
        if ms <= 0:
            return offset_ms
        self.append(Silence(ms, offset_ms=offset_ms))
        return offset_ms + ms
