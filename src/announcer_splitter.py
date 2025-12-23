#!/usr/bin/env python3
"""Split announcer recording into per-key WAVs based on _ANNOUNCER.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from ruamel import yaml

from segment_splitter import SegmentSplitter
import paths


@dataclass
class AnnouncerSplitter(SegmentSplitter):
    role: str = "_ANNOUNCER"

    def _load_announcer_yaml(self) -> dict:
        yaml_path = paths.MARKDOWN_ROLES_DIR / "_ANNOUNCER.yaml"
        if not yaml_path.exists():
            raise RuntimeError(f"Announcer YAML missing: {yaml_path}")
        yml = yaml.YAML()
        data = yml.load(yaml_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise RuntimeError(f"Invalid announcer YAML format: {yaml_path}")
        return data

    def _flatten_keys(self, node, prefix=None):
        keys: list[str] = []
        if isinstance(node, dict):
            for k, v in node.items():
                new_prefix = f"{prefix}-{k}" if prefix else str(k)
                keys.extend(self._flatten_keys(v, new_prefix))
        else:
            if prefix is None:
                raise RuntimeError("Unexpected scalar without key path in announcer YAML")
            keys.append(prefix)
        return keys

    def expected_ids(self, part_filter: str | None = None) -> list[str]:
        data = self._load_announcer_yaml()
        return self._flatten_keys(data)

    def pre_export_spans(self, spans, expected_ids, source_path: Path):
        if not spans:
            logging.warning("Expected announcer intro but found no spans to split")
            return spans
        # First span is the reader intro
        readers_dir = paths.BUILD_DIR / "audio" / "readers"
        readers_dir.mkdir(parents=True, exist_ok=True)
        self.splitter.export_spans(
            source_path,
            [spans[0]],
            ["_ANNOUNCER"],
            readers_dir,
            chunk_exports=False,
            cleanup_existing=False,
        )
        return spans[1:]

    def output_dir(self) -> Path:
        return paths.SEGMENTS_DIR / "_ANNOUNCER"
