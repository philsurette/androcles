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
    ignorable_extras: set[str] = field(default_factory=set)
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
        equivalencies = raw
        if "equivalencies" in raw or "ignorables" in raw:
            unexpected = [key for key in raw if key not in {"equivalencies", "ignorables"}]
            if unexpected:
                raise RuntimeError(f"Unexpected substitutions keys in {path}: {unexpected}")
            equivalencies = raw.get("equivalencies") or {}
            if not isinstance(equivalencies, dict):
                raise RuntimeError(f"Invalid equivalencies format in {path}")
            inst._load_ignorables(raw.get("ignorables"), path)
        for key, value in equivalencies.items():
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

    @classmethod
    def load_many(cls, paths: list[Path]) -> "Equivalencies":
        merged = cls()
        for path in paths:
            loaded = cls.load(path)
            merged._merge(loaded)
        return merged

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

    def is_ignorable_extra(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        if not normalized:
            return False
        for ignorable in self.ignorable_extras:
            if ignorable in normalized:
                return True
        return False

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

    def _merge(self, other: "Equivalencies") -> None:
        for key, values in other.global_map.items():
            self.global_map.setdefault(key, set()).update(values)
        for segment_id, scoped in other.scoped_map.items():
            target = self.scoped_map.setdefault(segment_id, {})
            for key, values in scoped.items():
                target.setdefault(key, set()).update(values)
        self.ignorable_extras.update(other.ignorable_extras)

    def _load_ignorables(self, raw: object, path: Path) -> None:
        if raw is None:
            return
        values: list[str]
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, (list, tuple, set)):
            values = [item for item in raw if isinstance(item, str)]
            if len(values) != len(raw):
                raise RuntimeError(f"Invalid ignorables in {path}: {raw!r}")
        else:
            raise RuntimeError(f"Invalid ignorables in {path}: {raw!r}")
        for value in values:
            normalized = self._normalize_text(value)
            if normalized:
                self.ignorable_extras.add(normalized)
