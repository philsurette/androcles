#!/usr/bin/env python3
"""Container class for audio plans."""
from __future__ import annotations

from typing import Iterable, TypeVar, Generic, List

from clip import Clip
from chapter_builder import Chapter

PlanItem = Clip | Chapter
T = TypeVar("T", bound=PlanItem)


class AudioPlan(List[T], Generic[T]):
    """Simple list subclass to represent an ordered audio plan."""

    def __init__(self, items: Iterable[T] | None = None) -> None:
        super().__init__(items or [])
