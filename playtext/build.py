#!/usr/bin/env python3
"""Build normalized paragraphs, parts, and per-character block files."""
from pathlib import Path

import paragraphs as pg
import blocks
import roles
import narration


def build_paragraphs() -> None:
    text = pg.SRC_PATH.read_text(encoding="utf-8-sig")
    paragraphs = pg.collapse_to_paragraphs(text)
    if paragraphs:
        pg.OUT_PATH.write_text("\n".join(paragraphs) + "\n", encoding="utf-8")
    else:
        pg.OUT_PATH.write_text("", encoding="utf-8")


def build_blocks() -> None:
    blocks.prepare_output_dirs()
    _, block_map, index = blocks.parse()
    blocks.write_blocks(block_map)
    blocks.write_index(index)
    roles.build_roles()
    narration.build_narration()


def main() -> None:
    build_paragraphs()
    build_blocks()


if __name__ == "__main__":
    main()
