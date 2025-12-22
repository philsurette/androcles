#!/usr/bin/env python3
"""Generate narrator cue script from PlayText."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

import paths
from play import Play, PlayTextParser, DescriptionBlock, DirectionBlock, MetaBlock, RoleBlock
from segment import DirectionSegment, SpeechSegment


@dataclass
class NarrationCues:
    play: Play

    def __post_init__(self) -> None:
        if self.play is None:
            self.play = PlayTextParser().parse()

    def write(self) -> None:
        """Generate narrator cues into build/markdown/roles/_NARRATOR.txt."""
        paths.MARKDOWN_ROLES_DIR.mkdir(parents=True, exist_ok=True)
        out_path = paths.MARKDOWN_ROLES_DIR / "_NARRATOR.txt"

        entries: List[str] = []
        meta_counters: Dict[int | None, int] = {}
        current_part: int | None = None
        block_counter = 0

        for blk in self.play:
            if blk.block_id.part_id != current_part:
                current_part = blk.block_id.part_id
                block_counter = 0
                if isinstance(blk, MetaBlock) and blk.text.startswith("##"):
                    title = blk.text
                    entries.append("\n".join([f"{current_part}:0", f"  - {title.strip()}"]))
                    continue

            if isinstance(blk, MetaBlock) and not blk.text.startswith("##"):
                key = blk.block_id.part_id
                meta_counters[key] = meta_counters.get(key, 0) + 1
                header = f"{'' if key is None else key}:{meta_counters[key]} META"
                entries.append("\n".join([header, f"  - {blk.text}"]))
                continue

            if isinstance(blk, (DescriptionBlock, DirectionBlock)):
                block_counter += 1
                header = f"{'' if blk.block_id.part_id is None else blk.block_id.part_id}:{blk.block_id.block_no} _NARRATOR"
                entries.append("\n".join([header] + [f"  - {seg.text}" for seg in blk.segments if getattr(seg, 'text', '').strip()]))
                continue

            if isinstance(blk, RoleBlock):
                block_counter += 1
                directions = []
                for seg in blk.segments:
                    text = getattr(seg, "text", "").strip()
                    if not text:
                        continue
                    if isinstance(seg, DirectionSegment):
                        directions.append(f"  - {text}")
                    elif isinstance(seg, SpeechSegment) and getattr(seg, "role", "") == "_NARRATOR":
                        directions.append(f"  - {text}")
                if directions:
                    header = f"{'' if blk.block_id.part_id is None else blk.block_id.part_id}:{blk.block_id.block_no} {blk.role_name}"
                    entries.append("\n".join([header] + directions))

        content = "\n\n".join(entries)
        if content:
            content += "\n"
        out_path.write_text(content, encoding="utf-8")
        logging.info("✅ wrote %s", out_path)


if __name__ == "__main__":
    NarrationCues(play=None).write()
