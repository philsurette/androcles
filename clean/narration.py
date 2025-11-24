#!/usr/bin/env python3
"""Generate narrator script containing descriptions and stage directions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent
BLOCKS_DIR = ROOT / "blocks"
ROLES_DIR = ROOT / "roles"
INDEX_PATH = BLOCKS_DIR / "_INDEX.txt"

HEADER_RE = re.compile(r"^(\d+):(\d+)$")


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
    blocks: Dict[str, Dict[Tuple[str, str], List[str]]] = {}
    for path in BLOCKS_DIR.glob("*.txt"):
        if path.name == "_INDEX.txt":
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

    output_entries: List[str] = []

    for part_id, block_no, target in index_entries:
        key = (part_id, block_no)
        block_map = blocks_map.get(target)
        if not block_map or key not in block_map:
            continue
        lines = block_map[key]

        label = target.lstrip("_").upper()

        if target in {"_DESCRIPTION", "_DIRECTION"}:
            header = f"{part_id}:{block_no} {label}"
            entry_lines = [header] + lines[1:]
            output_entries.append("\n".join(entry_lines))
            continue

        directions = collect_inline_directions(lines)
        if directions:
            header = f"{part_id}:{block_no} {target}"
            entry_lines = [header] + directions
            output_entries.append("\n".join(entry_lines))

    content = "\n\n".join(output_entries)
    if content:
        content += "\n"
    (ROLES_DIR / "_NARRATOR.txt").write_text(content, encoding="utf-8")


def main() -> None:
    build_narration()


if __name__ == "__main__":
    main()
