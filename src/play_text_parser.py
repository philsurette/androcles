#!/usr/bin/env python3
"""Parse play text into Play and Blocks."""
from __future__ import annotations

from pathlib import Path
import logging
from ruamel import yaml
import re
from typing import List

import paths
from play import Play, SourceTextMetadata, ReadingMetadata, Reader
from block import Block, TitleBlock, DescriptionBlock, DirectionBlock, RoleBlock


class PlayTextParser:
    """Parse a source play text file into a PlayText of Blocks."""

    def __init__(self, source_path: Path | None = None) -> None:
        # Prefer the normalized paragraphs file when available to align numbering
        self.source_path = source_path or paths.DEFAULT_PLAY

    def _load_source_text_metadata(self) -> SourceTextMetadata:
        """Load source text metadata from YAML adjacent to play.txt."""
        meta_path = self.source_path.with_name("source_text_metadata.yaml")
        if not meta_path.exists():
            logging.warning(f"could not find source text metadata at {meta_path}")
            return SourceTextMetadata()
        yml = yaml.YAML(typ='safe', pure=True)
        raw = yml.load(meta_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid metadata format in {meta_path}")
        return SourceTextMetadata(**raw)
    
    def _load_reading_metadata(self) -> ReadingMetadata:
        meta_path = self.source_path.with_name("reading_metadata.yaml")
        if not meta_path.exists():
            logging.warning(f"could not find reading metadata at {meta_path}")
            return ReadingMetadata()
        yml = yaml.YAML(typ='safe', pure=True)
        raw = yml.load(meta_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid metadata format in {meta_path}")
        readers: list[Reader] = []
        for entry in raw.get("readers", []) or []:
            if isinstance(entry, dict):
                readers.append(Reader(**entry))
            elif isinstance(entry, Reader):
                readers.append(entry)
            else:
                logging.warning("Skipping unexpected reader entry %r in %s", entry, meta_path)

        meta_kwargs = dict(raw)
        meta_kwargs["readers"] = readers
        return ReadingMetadata(**meta_kwargs)

    def collapse_to_paragraphs(self, text: str) -> list[str]:
        """
        Join consecutive non-empty lines with spaces and use blank lines as
        paragraph boundaries, without emitting blank lines.
        """
        output: list[str] = []
        buffer: list[str] = []

        for raw_line in text.splitlines():
            # Treat any whitespace-only line as a boundary.
            if raw_line.strip():
                buffer.append(raw_line.strip())
            else:
                if buffer:
                    output.append(" ".join(buffer))
                    buffer.clear()

        if buffer:
            output.append(" ".join(buffer))

        return output

    def parse(self) -> Play:
        raw_text = self.source_path.read_text(encoding="utf-8-sig")
        paragraphs = self.collapse_to_paragraphs(raw_text)

        metadata = self._load_source_text_metadata()
        reading_metadata = self._load_reading_metadata()
        play = Play(source_text_metadata=metadata, reading_metadata=reading_metadata)
        current_part: int | None = None
        block_counter = 0
        meta_counters: dict[int | None, int] = {}

        for paragraph in paragraphs:
            if not paragraph:
                continue

            previous_block_counter = block_counter
            # Try each block type in order.
            parsed_block: Block | None = None
            for cls in (TitleBlock, DescriptionBlock, DirectionBlock, RoleBlock):
                block = cls.parse(paragraph, current_part, block_counter, meta_counters)
                if block is not None:
                    parsed_block = block
                    break

            if parsed_block is None:
                raise RuntimeError(f"Unable to parse paragraph into any block type: {paragraph}")

            play.blocks.append(parsed_block)
            play._by_id[parsed_block.block_id] = parsed_block
            current_part = parsed_block.block_id.part_id
            if isinstance(parsed_block, TitleBlock) and not parsed_block.text.startswith("##"):
                # Inline meta paragraphs should not advance the speech block counter.
                block_counter = previous_block_counter
            else:
                block_counter = parsed_block.block_id.block_no

        play.rebuild_parts_index()
        return play
