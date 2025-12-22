#!/usr/bin/env python3
"""Generate role cue scripts from PlayText."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import logging

import paths
from play import Play, PlayTextParser, RoleBlock
from segment import DirectionSegment, SpeechSegment


@dataclass
class RoleCues:
    play: Play

    def __post_init__(self) -> None:
        if self.play is None:
            self.play = PlayTextParser().parse()

    def shorten_cue_lines(self, lines: List[str]) -> List[str]:
        """
        Limit cue text to a maximum of 20 words; if longer, include the last
        10 words with a leading ellipsis, preserving line order from the end.
        When pulling earlier lines to reach the 10-word minimum, include the
        whole line if it is 13 words or fewer; otherwise include its last
        10 words, and prefix the ellipsis with the first three words of that line.
        """
        meta = [(line, line.strip().startswith("(_")) for line in lines]
        total_words = sum(len(line.split()) for line in lines)
        if total_words <= 20:
            return lines

        remaining = 10
        collected: List[tuple[str, bool, bool, str]] = []
        for line, is_direction in reversed(meta):
            words = line.split()
            if not words:
                continue

            if len(words) <= 13:
                segment = " ".join(words)
                truncated_segment = False
                prefix = ""
                count = len(words)
            else:
                segment = " ".join(words[-10:])
                truncated_segment = True
                prefix = " ".join(words[:3])
                count = 10

            collected.append((segment, is_direction, truncated_segment, prefix))
            remaining -= count
            if remaining <= 0:
                break

        collected = list(reversed(collected))
        if collected:
            segment, is_direction, truncated_segment, prefix = collected[0]
            if truncated_segment and not segment.lstrip().startswith("..."):
                segment = f"{prefix} ... {segment}".strip()

            if is_direction:
                cleaned = segment.strip()
                has_ellipsis = False
                if cleaned.startswith("..."):
                    has_ellipsis = True
                    cleaned = cleaned[3:].lstrip()
                if cleaned.startswith("(_"):
                    cleaned = cleaned[2:].lstrip()
                rebuilt = "(_ "
                if has_ellipsis:
                    rebuilt += "... "
                rebuilt += cleaned
                segment = rebuilt
            collected[0] = (segment, is_direction, truncated_segment, prefix)

        return [segment for segment, _, _, _ in collected]

    def last_speech_snippet(self, lines: List[str]) -> str:
        """Return up to 10 trailing words (with prefix if cropped) from the last spoken line."""
        for line in reversed(lines):
            text = line.strip()
            if not text or text.startswith("(_"):
                continue
            words = text.split()
            if len(words) <= 13:
                return " ".join(words)
            prefix = " ".join(words[:3])
            tail = " ".join(words[-10:])
            return f"{prefix} ... {tail}"
        return ""

    def write(self) -> None:
        """Generate role cue files into build/roles."""
        paths.MARKDOWN_ROLES_DIR.mkdir(parents=True, exist_ok=True)
        for path in paths.MARKDOWN_ROLES_DIR.glob("*.txt"):
            path.unlink()

        role_entries: Dict[str, List[str]] = {}
        previous_block: RoleBlock | None = None

        for blk in self.play:
            if not isinstance(blk, RoleBlock):
                previous_block = blk if isinstance(blk, RoleBlock) else None
                continue

            speaker_list = blk.speakers if getattr(blk, "speakers", None) else [blk.role_name]
            if any(r.startswith("_") for r in speaker_list):
                previous_block = blk
                continue

            header = f"{'' if blk.block_id.part_id is None else blk.block_id.part_id}:{blk.block_id.block_no}"
            cue_label = ""
            cue_lines: List[str] = []

            if previous_block and isinstance(previous_block, RoleBlock):
                cue_label = previous_block.role_name.lstrip("_")
                cue_texts = [str(seg) for seg in previous_block.segments if getattr(seg, "text", "").strip()]
                cue_lines = self.shorten_cue_lines(cue_texts)
                if cue_lines and cue_lines[0].lstrip().startswith("(_"):
                    speech_snip = self.last_speech_snippet(cue_texts)
                    if speech_snip and speech_snip not in cue_lines:
                        cue_lines.append(speech_snip)

            if cue_label:
                header = f"{header} < {cue_label}"

            lines: List[str] = [header]
            if cue_lines:
                lines.extend([f"    # {line}" for line in cue_lines])

            for seg in blk.segments:
                text = getattr(seg, "text", "").strip()
                if not text:
                    continue
                lines.append(f"- {text}")

            for role_name in speaker_list:
                role_entries.setdefault(role_name, []).append("\n".join(lines))
            previous_block = blk

        for role, entries in role_entries.items():
            path = paths.MARKDOWN_ROLES_DIR / f"{role}.txt"
            content = "\n\n".join(entries)
            if content:
                content += "\n"
            path.write_text(content, encoding="utf-8")
            logging.info("✅ wrote %s", path)


if __name__ == "__main__":
    RoleCues(play=None).write()
