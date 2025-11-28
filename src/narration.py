#!/usr/bin/env python3
"""Generate narrator script containing descriptions and stage directions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from paths import BLOCKS_DIR, ROLES_DIR, PARAGRAPHS_PATH, BLOCKS_EXT, INDEX_PATH

HEADER_RE = re.compile(r"^(\d+):(\d+)$")
PART_HEADING_RE = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
META_RE = re.compile(r"^::(.*)::$")
DESCRIPTION_RE = re.compile(r"^\[\[(.*)\]\]$")
STAGE_RE = re.compile(r"^_+(.*?)_+\s*$")
BLOCK_RE = re.compile(r"^[A-Z][A-Z '()-]*?\.\s*.*$")


def load_index() -> List[Tuple[str, str, str]]:
    entries: List[Tuple[str, str, str]] = []
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        left, target = line.split(maxsplit=1)
        part_id, block_no = left.split(":")
        entries.append((part_id, block_no, target))
    return entries


def parse_block_file(path: Path) -> Dict[Tuple[str, str], List[str]]:
    content: Dict[Tuple[str, str], List[str]] = {}
    current_key: Tuple[str, str] | None = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            content[current_key] = current_lines
        current_key = None
        current_lines = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if HEADER_RE.match(raw_line.strip()):
            flush()
            part_id, block_no = raw_line.strip().split(":")
            current_key = (part_id, block_no)
            current_lines = [raw_line.strip()]
        else:
            if current_key is not None:
                current_lines.append(raw_line)

    flush()
    return content


def load_blocks() -> Dict[str, Dict[Tuple[str, str], List[str]]]:
    """Load all block files into a mapping by target name."""
    blocks: Dict[str, Dict[Tuple[str, str], List[str]]] = {}
    for path in BLOCKS_DIR.glob(f"*{BLOCKS_EXT}"):
        if path.name == f"_INDEX{BLOCKS_EXT}":
            continue
        blocks[path.stem] = parse_block_file(path)
    return blocks


def collect_inline_directions(block_lines: List[str]) -> List[str]:
    """Return bullet lines that are inline directions."""
    return [line for line in block_lines[1:] if line.strip().startswith("- (_")]


def build_narration() -> None:
    ROLES_DIR.mkdir(parents=True, exist_ok=True)
    blocks_map = load_blocks()
    index_entries = load_index()
    index_lookup = {(p, b): t for p, b, t in index_entries}

    output_entries: List[str] = []
    meta_counters: Dict[str, int] = {}
    current_part: str | None = None
    block_counter = 0

    for line in PARAGRAPHS_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue

        part_match = PART_HEADING_RE.match(line)
        if part_match:
            current_part = part_match.group(1)
            block_counter = 0
            part_name = part_match.group(2).strip()
            output_entries.append("\n".join([f"{current_part}:0", f"  - {part_name}"]))
            continue

        meta_match = META_RE.match(line)
        if meta_match:
            part_key = current_part if current_part is not None else ""
            meta_counters[part_key] = meta_counters.get(part_key, 0) + 1
            header = f"{part_key}:{meta_counters[part_key]} META"
            output_entries.append("\n".join([header, f"  - {meta_match.group(1).strip()}"]))
            continue

        if DESCRIPTION_RE.match(line):
            if current_part is None:
                continue
            block_counter += 1
            target = index_lookup.get((current_part, str(block_counter)))
            if target:
                block_map = blocks_map.get(target)
                key = (current_part, str(block_counter))
                if block_map and key in block_map:
                    lines = block_map[key]
                    header = f"{current_part}:{block_counter} {target.lstrip('_').upper()}"
                    output_entries.append("\n".join([header] + lines[1:]))
            continue

        if STAGE_RE.match(line):
            if current_part is None:
                continue
            block_counter += 1
            target = index_lookup.get((current_part, str(block_counter)))
            if target:
                block_map = blocks_map.get(target)
                key = (current_part, str(block_counter))
                if block_map and key in block_map:
                    lines = block_map[key]
                    header = f"{current_part}:{block_counter} {target.lstrip('_').upper()}"
                    output_entries.append("\n".join([header] + lines[1:]))
            continue

        if BLOCK_RE.match(line):
            if current_part is None:
                continue
            block_counter += 1
            target = index_lookup.get((current_part, str(block_counter)))
            if target:
                block_map = blocks_map.get(target)
                key = (current_part, str(block_counter))
                if block_map and key in block_map:
                    lines = block_map[key]
                    directions = collect_inline_directions(lines)
                    if directions:
                        header = f"{current_part}:{block_counter} {target}"
                        output_entries.append("\n".join([header] + directions))

    content = "\n\n".join(output_entries)
    if content:
        content += "\n"
    (ROLES_DIR / "_NARRATOR.txt").write_text(content, encoding="utf-8")


def main() -> None:
    build_narration()


if __name__ == "__main__":
    main()
