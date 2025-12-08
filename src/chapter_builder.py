#!/usr/bin/env python3
"""Build chapter markers from PlayText parts and description blocks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from play_text import PlayText
from chapter import Chapter

@dataclass
class ChapterBuilder:
    """Create Chapter entries from a PlayText."""

    play_text: PlayText

    def build(self) -> List[Chapter]:
        chapters: List[Chapter] = []
        for part in self.play_text.getParts():
            part_id = part.part_no
            if part_id is None:
                # Skip preamble; chapters are keyed to numbered parts.
                continue
            part_title = part.title or ""

            chapters.append(Chapter(block_id=f"{part_id}:0", title=part_title))
        return chapters
