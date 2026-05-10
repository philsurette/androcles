#!/usr/bin/env python3
"""Collect unresolved replacement diffs and write them as equivalencies YAML."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString


@dataclass
class UnresolvedDiffs:
    entries: dict[str, set[str]] = field(default_factory=dict)
    _space_re: re.Pattern[str] = field(default_factory=lambda: re.compile(r"\s+"))
    _token_re: re.Pattern[str] = field(default_factory=lambda: re.compile(r"[A-Za-z0-9']+"))

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
            equivalencies[self._format_key(key)] = seq
        output["equivalencies"] = equivalencies
        yml = YAML()
        yml.default_flow_style = False
        with path.open("w", encoding="utf-8") as handle:
            yml.dump(output, handle)
        return path

    def _normalize_phrase(self, text: str) -> str:
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        tokens = self._token_re.findall(text)
        words: list[str] = []
        for token in tokens:
            token = token.replace("'", "")
            if token:
                words.append(token)
        text = " ".join(words)
        text = self._space_re.sub(" ", text).strip()
        return text

    def _format_key(self, key: str) -> str:
        if self._needs_quotes(key):
            return DoubleQuotedScalarString(key)
        return key

    def _needs_quotes(self, key: str) -> bool:
        for char in key:
            if char.isspace():
                return True
            if not char.isalnum() and char not in {"@", "_"}:
                return True
        return False
