#!/usr/bin/env python3
"""Collect unresolved replacement diffs and write them as equivalencies YAML."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq


@dataclass
class UnresolvedDiffs:
    entries: dict[str, set[str]] = field(default_factory=dict)
    _space_re: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\s+"))

    def add(self, expected: str, actual: str, segment_id: str | None = None) -> None:
        expected_clean = self._normalize_phrase(expected)
        actual_clean = self._normalize_phrase(actual)
        if not expected_clean or not actual_clean or expected_clean == actual_clean:
            return
        key = f"{expected_clean}@{segment_id}" if segment_id else expected_clean
        self.entries.setdefault(key, set()).add(actual_clean)

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        output = CommentedMap()
        equivalencies = CommentedMap()
        for key in sorted(self.entries):
            values = sorted(self.entries[key])
            seq = CommentedSeq(values)
            seq.fa.set_flow_style()
            equivalencies[key] = seq
        output["equivalencies"] = equivalencies
        yml = YAML()
        yml.default_flow_style = False
        with path.open("w", encoding="utf-8") as handle:
            yml.dump(output, handle)
        return path

    def _normalize_phrase(self, text: str) -> str:
        text = text.strip()
        text = self._space_re.sub(" ", text)
        return text
