#!/usr/bin/env python3
"""
Generate per-part and per-character block files from the normalized paragraphs.

Outputs:
- parts/<part_id>_<slug>.txt : paragraphs belonging to each part
- blocks/<CHARACTER>.txt     : each block line prefixed with part:block_number
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT.parent / "build"
PARAGRAPHS_PATH = ROOT / "paragraphs.txt"
PARTS_DIR = BUILD_DIR / "parts"
BLOCKS_DIR = BUILD_DIR / "blocks"

PART_HEADING_RE = re.compile(r"^##\s*(\d+)\s*[:.]\s*(.*?)\s*##$")
BLOCK_RE = re.compile(r"^([A-Z][A-Z '()-]*?)\.\s*(.*)$")
DESCRIPTION_RE = re.compile(r"^\[\[(.*)\]\]$")
STAGE_RE = re.compile(r"^_+(.*?)_+\s*$")
META_RE = re.compile(r"^::(.*)::$")


def slugify(name: str) -> str:
    """Create a filesystem-friendly slug from a part name."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_").lower()
    return slug or "part"


def read_paragraphs() -> List[str]:
    """Read the normalized paragraphs file into a list of paragraph strings."""
    text = PARAGRAPHS_PATH.read_text(encoding="utf-8-sig")
    return [line.rstrip("\n") for line in text.splitlines()]


def write_part(part_id: str, part_name: str, paragraphs: List[str]) -> None:
    """Write collected paragraphs for a part to parts/<id>_<slug>.txt."""
    slug = slugify(part_name)
    path = PARTS_DIR / f"{part_id}_{slug}.txt"
    content = "\n".join(paragraphs)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def write_blocks(blocks: Dict[str, List[str]]) -> None:
    """Write per-character block lines to blocks/<CHARACTER>.txt."""
    for character, entries in blocks.items():
        content = "\n".join(entries)
        if content:
            content += "\n"
        (BLOCKS_DIR / f"{character}.txt").write_text(content, encoding="utf-8")


def prepare_output_dirs() -> None:
    """Ensure output directories exist and are cleared of old .txt files."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (PARTS_DIR, BLOCKS_DIR):
        for path in folder.glob("*.txt"):
            path.unlink()


def parse() -> Tuple[Dict[str, List[str]], Dict[str, List[str]], List[Tuple[str, int, str]]]:
    """
    Parse paragraphs into parts and character blocks.

    Returns a tuple of:
    - parts: mapping part_id -> list of paragraph strings (excluding headings)
    - blocks: mapping character name -> list of numbered block strings
    - index: list of tuples (part_id, block_no, target_name)
    """
    parts: Dict[str, List[str]] = {}
    blocks: Dict[str, List[str]] = {}
    index: List[Tuple[str, int, str]] = []
    meta_counters: Dict[str, int] = {}

    current_part_id = None
    current_part_name = None
    current_paragraphs: List[str] = []
    block_counter = 0

    for paragraph in read_paragraphs():
        if not paragraph:
            # Skip empty lines; paragraphs.txt should not contain these.
            continue

        part_match = PART_HEADING_RE.match(paragraph)
        if part_match:
            # Flush previous part, if any.
            if current_part_id is not None:
                parts[current_part_id] = list(current_paragraphs)
                write_part(current_part_id, current_part_name or "", current_paragraphs)
            current_part_id, current_part_name = part_match.groups()
            current_paragraphs = []
            block_counter = 0
            heading_entry = format_block_entry(current_part_id, 0, [current_part_name.strip()])
            blocks.setdefault("_HEADING", []).append(heading_entry)
            index.append((current_part_id, 0, "_HEADING"))
            continue

        # Ignore content before the first part heading.
        if current_part_id is None:
            meta_match = META_RE.match(paragraph)
            if meta_match:
                part_key = ""
                meta_counters[part_key] = meta_counters.get(part_key, 0) + 1
                entry = format_block_entry(part_key, meta_counters[part_key], [meta_match.group(1).strip()], label="META")
                blocks.setdefault("_META", []).append(entry)
                index.append((part_key, meta_counters[part_key], "_META"))
            continue

        current_paragraphs.append(paragraph)

        meta_match = META_RE.match(paragraph)
        if meta_match:
            part_key = current_part_id
            meta_counters[part_key] = meta_counters.get(part_key, 0) + 1
            entry = format_block_entry(part_key, meta_counters[part_key], [meta_match.group(1).strip()], label="META")
            blocks.setdefault("_META", []).append(entry)
            index.append((part_key, meta_counters[part_key], "_META"))
            continue

        desc_text = extract_description(paragraph)
        if desc_text is not None:
            block_counter += 1
            entry = format_block_entry(current_part_id, block_counter, [desc_text])
            target = "_DESCRIPTION"
            blocks.setdefault(target, []).append(entry)
            index.append((current_part_id, block_counter, target))
            continue

        stage_text = extract_stage_direction(paragraph)
        if stage_text is not None:
            block_counter += 1
            entry = format_block_entry(current_part_id, block_counter, [stage_text])
            target = "_DIRECTION"
            blocks.setdefault(target, []).append(entry)
            index.append((current_part_id, block_counter, target))
            continue

        block_match = BLOCK_RE.match(paragraph)
        if block_match:
            character, speech = block_match.groups()
            block_counter += 1
            speech_text = speech.strip()
            segments = split_block_segments(speech_text)
            entry = format_block_entry(current_part_id, block_counter, segments)
            blocks.setdefault(character, []).append(entry)
            index.append((current_part_id, block_counter, character))

    # Flush the final part.
    if current_part_id is not None:
        parts[current_part_id] = list(current_paragraphs)
        write_part(current_part_id, current_part_name or "", current_paragraphs)

    return parts, blocks, index


def main() -> None:
    prepare_output_dirs()
    _, blocks, index = parse()
    write_blocks(blocks)
    write_index(index)


def split_block_segments(text: str) -> List[str]:
    """
    Split a block of speech into direction and spoken segments.

    - Sequences enclosed in '(_' and '_)' are treated as stage directions.
    - Text before, after, or between directions is split into its own segment.
    - Whitespace around segments is stripped.
    """
    segments: List[str] = []
    pattern = re.compile(r"\(_.*?_\)")
    last_end = 0

    for match in pattern.finditer(text):
        pre = text[last_end : match.start()]
        if pre.strip():
            segments.append(pre.strip())

        direction = match.group(0)
        # Attach immediate trailing punctuation (e.g., ".") to the direction.
        punct_end = match.end()
        while punct_end < len(text) and text[punct_end] in ".,;:!?":
            direction += text[punct_end]
            punct_end += 1

        direction = direction.strip()
        if direction:
            segments.append(direction)
        last_end = punct_end

    tail = text[last_end:]
    if tail.strip():
        segments.append(tail.strip())

    return segments


def extract_description(paragraph: str) -> Optional[str]:
    """Return inner text of [[...]] descriptions, if present."""
    match = DESCRIPTION_RE.match(paragraph.strip())
    if not match:
        return None
    return match.group(1).strip()


def extract_stage_direction(paragraph: str) -> Optional[str]:
    """Return inner text of _..._ stage paragraphs, if present."""
    match = STAGE_RE.match(paragraph.strip())
    if not match:
        return None
    return match.group(1).strip()


def format_block_entry(part_id: str, block_no: int, segments: List[str], label: Optional[str] = None) -> str:
    """Render a block entry with a header and bullet-pointed segments."""
    header = f"{part_id}:{block_no}" if part_id is not None else f":{block_no}"
    if label:
        header = f"{header} {label}"
    lines = [header]
    for segment in segments:
        if segment:
            lines.append(f"  - {segment}")
    return "\n".join(lines)


def write_index(index_entries: List[Tuple[str, int, str]]) -> None:
    """Write a master index mapping part:block to destination file."""
    lines = []
    for part_id, block_no, target in index_entries:
        lines.append(f"{part_id}:{block_no} {target}")
    content = "\n".join(lines)
    if content:
        content += "\n"
    (BLOCKS_DIR / "_INDEX.txt").write_text(content, encoding="utf-8")




if __name__ == "__main__":
    main()
