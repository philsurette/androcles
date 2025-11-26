#!/usr/bin/env python3
"""Generate role scripts with cues from blocks outputs."""
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
    """Read the global index as a list of (part_id, block_no, target)."""
    entries: List[Tuple[str, str, str]] = []
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        left, target = line.split(maxsplit=1)
        part_id, block_no = left.split(":")
        entries.append((part_id, block_no, target))
    return entries


def parse_block_file(path: Path) -> Dict[Tuple[str, str], List[str]]:
    """Return a mapping {(part_id, block_no): [lines]} for a block file."""
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
    for path in BLOCKS_DIR.glob("*.txt"):
        if path.name == "_INDEX.txt":
            continue
        blocks[path.stem] = parse_block_file(path)
    return blocks


def ensure_roles_dir() -> None:
    ROLES_DIR.mkdir(parents=True, exist_ok=True)
    for path in ROLES_DIR.glob("*.txt"):
        path.unlink()


def cue_lines(
    cue_target: str, cue_key: Tuple[str, str], blocks_map: Dict[str, Dict[Tuple[str, str], List[str]]]
) -> Tuple[str, List[str]]:
    """Return cue label and formatted cue lines for the given target/key."""
    cue_blocks = blocks_map.get(cue_target)
    if not cue_blocks:
        return "", []
    cue = cue_blocks.get(cue_key)
    if not cue:
        return "", []
    part_id, block_no = cue_key
    label = cue_target.lstrip("_")

    cue_body: List[str] = []
    for line in cue[1:]:
        text = line.strip()
        if text.startswith("- "):
            text = text[2:]
        elif text.startswith("-"):
            text = text[1:].strip()
        elif text.startswith("#"):
            text = text[1:].strip()
        cue_body.append(text)

    shortened = shorten_cue_lines(cue_body)
    lines: List[str] = [f"    # {text}" for text in shortened]

    if shortened and shortened[0].lstrip().startswith("(_"):
        speech_snippet = last_speech_snippet(cue_body)
        snippet_line = f"    # {speech_snippet}" if speech_snippet else ""
        if speech_snippet and snippet_line not in lines:
            lines.append(snippet_line)

    return label, lines


def build_roles() -> None:
    ensure_roles_dir()
    index_entries = load_index()
    blocks_map = load_blocks()

    role_entries: Dict[str, List[str]] = {role: [] for role in blocks_map.keys() if not role.startswith("_")}

    for idx, (part_id, block_no, target) in enumerate(index_entries):
        if target.startswith("_"):
            continue  # skip special files for role ownership

        block_key = (part_id, block_no)
        block_lines = blocks_map[target].get(block_key)
        if not block_lines:
            continue

        # Build cue if available.
        cue_lines_block: List[str] = []
        cue_label = ""
        if idx > 0:
            cue_part, cue_no, cue_target = index_entries[idx - 1]
            cue_label, cue_lines_block = cue_lines(cue_target, (cue_part, cue_no), blocks_map)

        output_lines: List[str] = []
        header_line = block_lines[0]
        if cue_label:
            header_line = f"{header_line} < {cue_label}"
        output_lines.append(header_line)
        if cue_lines_block:
            output_lines.extend(cue_lines_block)
        output_lines.extend(block_lines[1:])  # original bullet lines
        role_entries[target].append("\n".join(output_lines))

    for role, entries in role_entries.items():
        path = ROLES_DIR / f"{role}.txt"
        content = "\n\n".join(entries)
        if content:
            content += "\n"
        path.write_text(content, encoding="utf-8")


def shorten_cue_lines(lines: List[str]) -> List[str]:
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
    collected: List[Tuple[str, bool, bool, str]] = []
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
        # If we truncated the overall cue, mark the leading segment with an ellipsis.
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


def last_speech_snippet(lines: List[str]) -> str:
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


def main() -> None:
    build_roles()


if __name__ == "__main__":
    main()
