#!/usr/bin/env python3
"""Build chapter markers from title blocks in paragraphs."""
from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import List

from paths import PARAGRAPHS_PATH

PART_HEADING_RE = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
DESCRIPTION_RE = re.compile(r"^\[\[(.*)\]\]$")
STAGE_RE = re.compile(r"^_+(.*?)_+\s*$")
BLOCK_RE = re.compile(r"^[A-Z][A-Z '()-]*?\.\s*.*$")

@dataclass(frozen=True)
class Chapter:
    block_id: str
    title: str
    offset_ms: int | None = None


class ChapterBuilder:
    """Create Chapter entries from part headings in paragraphs.txt."""

    def __init__(self, paragraphs_path: Path | None = None) -> None:
        self.paragraphs_path = paragraphs_path or PARAGRAPHS_PATH

    def build(self) -> List[Chapter]:
        chapters: List[Chapter] = []
        scene_counter = 0
        current_part: str | None = None
        current_title: str | None = None
        block_counter = 0
        prev_type: str | None = None  # "title", "description", "other"

        for line in self.paragraphs_path.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            heading = PART_HEADING_RE.match(stripped)
            if heading:
                part_id, title = heading.groups()
                current_part = part_id
                current_title = title.strip()
                scene_counter = 0
                block_counter = 0
                chapters.append(Chapter(block_id=f"{part_id}:0", title=current_title))
                prev_type = "title"
                continue

            desc = DESCRIPTION_RE.match(stripped)
            if desc:
                if current_part:
                    block_counter += 1
                    if prev_type not in ("description", "title"):
                        scene_counter += 1
                        title = f"{current_title}: Scene {scene_counter}" if current_title else f"Scene {scene_counter}"
                        chapters.append(Chapter(block_id=f"{current_part}:{block_counter}", title=title))
                prev_type = "description"
                continue

            if STAGE_RE.match(stripped) or BLOCK_RE.match(stripped):
                if current_part:
                    block_counter += 1
                prev_type = "other"
                continue

            prev_type = "other"

        return chapters
