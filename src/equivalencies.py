#!/usr/bin/env python3
"""Load and evaluate user-defined word equivalencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from ruamel import yaml


@dataclass
class Equivalencies:
    global_map: dict[str, set[str]] = field(default_factory=dict)
    scoped_map: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    _token_re: re.Pattern[str] = field(default_factory=lambda: re.compile(r"[A-Za-z0-9']+"))

    @classmethod
    def load(cls, path: Path) -> "Equivalencies":
        if not path.exists():
            return cls()
        yml = yaml.YAML(typ="safe", pure=True)
        raw = yml.load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise RuntimeError(f"Invalid equivalencies format in {path}")
        inst = cls()
        for key, value in raw.items():
            if not isinstance(key, str):
                raise RuntimeError(f"Invalid equivalencies key in {path}: {key!r}")
            segment_id = None
            if "@" in key:
                base, segment = key.split("@", 1)
                key = base
                segment_id = segment.strip()
            variants = inst._coerce_variants(value, path)
            for variant in variants:
                inst._add_pair(key, variant, segment_id)
        return inst

    def is_equivalent(self, expected: str, actual: str, segment_id: str | None = None) -> bool:
        expected_norm = self._normalize_text(expected)
        actual_norm = self._normalize_text(actual)
        if not expected_norm or not actual_norm:
            return False
        if expected_norm == actual_norm:
            return True
        if segment_id:
            scoped = self.scoped_map.get(segment_id)
            if scoped and self._map_contains(scoped, expected_norm, actual_norm):
                return True
        return self._map_contains(self.global_map, expected_norm, actual_norm)

    def _map_contains(self, mapping: dict[str, set[str]], left: str, right: str) -> bool:
        if right in mapping.get(left, set()):
            return True
        return left in mapping.get(right, set())

    def _add_pair(self, expected: str, actual: str, segment_id: str | None) -> None:
        expected_norm = self._normalize_text(expected)
        actual_norm = self._normalize_text(actual)
        if not expected_norm or not actual_norm or expected_norm == actual_norm:
            return
        if segment_id:
            scoped = self.scoped_map.setdefault(segment_id, {})
            scoped.setdefault(expected_norm, set()).add(actual_norm)
            scoped.setdefault(actual_norm, set()).add(expected_norm)
        else:
            self.global_map.setdefault(expected_norm, set()).add(actual_norm)
            self.global_map.setdefault(actual_norm, set()).add(expected_norm)

    def _coerce_variants(self, value: object, path: Path) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            variants = [item for item in value if isinstance(item, str)]
            if len(variants) != len(value):
                raise RuntimeError(f"Invalid equivalencies value in {path}: {value!r}")
            return variants
        raise RuntimeError(f"Invalid equivalencies value in {path}: {value!r}")

    def _normalize_text(self, text: str) -> str:
        tokens = self._token_re.findall(text)
        words: list[str] = []
        for token in tokens:
            token = token.lower().replace("\u2019", "'").replace("\u2018", "'")
            token = token.replace("'", "")
            if token:
                words.append(token)
        return " ".join(words)
