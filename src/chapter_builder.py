#!/usr/bin/env python3
"""Build chapter markers from title blocks in paragraphs."""
from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import List

from paths import PARAGRAPHS_PATH

PART_HEADING_RE = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")


@dataclass(frozen=True)
class Chapter:
    block_id: str
    title: str


class ChapterBuilder:
    """Create Chapter entries from part headings in paragraphs.txt."""

    def __init__(self, paragraphs_path: Path | None = None) -> None:
        self.paragraphs_path = paragraphs_path or PARAGRAPHS_PATH

    def build(self) -> List[Chapter]:
        chapters: List[Chapter] = []
        for line in self.paragraphs_path.read_text(encoding="utf-8-sig").splitlines():
            m = PART_HEADING_RE.match(line.strip())
            if not m:
                continue
            part_id, title = m.groups()
            block_id = f"{part_id}:0"
            chapters.append(Chapter(block_id=block_id, title=title.strip()))
        return chapters
