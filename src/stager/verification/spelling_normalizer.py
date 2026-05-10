#!/usr/bin/env python3
"""Normalize British/American spelling variants using breame."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Iterable


@dataclass
class SpellingNormalizer:
    variant_map: dict[str, set[str]] = field(default_factory=dict)
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self.variant_map = self._normalize_map(self.variant_map)

    @classmethod
    def from_breame(cls) -> "SpellingNormalizer":
        from breame import spelling as breame_spelling

        mapping = cls._extract_mappings(breame_spelling)
        if not mapping:
            raise RuntimeError("breame did not expose spelling mappings")
        return cls(variant_map=mapping)

    def is_equivalent(self, expected: str, actual: str) -> bool:
        if expected == actual:
            return True
        expected_variants = self.variant_map.get(expected, set())
        if actual in expected_variants:
            return True
        actual_variants = self.variant_map.get(actual, set())
        return expected in actual_variants

    @classmethod
    def _extract_mappings(cls, module) -> dict[str, set[str]]:
        candidates: list[dict[str, object]] = []
        for name in (
            "AMERICAN_ENGLISH_SPELLINGS",
            "BRITISH_ENGLISH_SPELLINGS",
        ):
            mapping = getattr(module, name, None)
            if isinstance(mapping, dict) and mapping:
                candidates.append(mapping)
        if not candidates:
            for attr_name in dir(module):
                mapping = getattr(module, attr_name)
                if isinstance(mapping, dict) and mapping:
                    if cls._looks_like_word_map(mapping):
                        candidates.append(mapping)
        merged: dict[str, set[str]] = {}
        for mapping in candidates:
            for key, value in mapping.items():
                if not isinstance(key, str):
                    continue
                for variant in cls._iter_variants(value):
                    merged.setdefault(key, set()).add(variant)
        return merged

    @classmethod
    def _iter_variants(cls, value: object) -> Iterable[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [item for item in value if isinstance(item, str)]
        return []

    @classmethod
    def _looks_like_word_map(cls, mapping: dict) -> bool:
        sample = list(mapping.items())[:5]
        if not sample:
            return False
        for key, value in sample:
            if not isinstance(key, str):
                return False
            if isinstance(value, str):
                continue
            if isinstance(value, (list, tuple, set)):
                if not all(isinstance(item, str) for item in value):
                    return False
                continue
            return False
        return True

    def _normalize_map(self, mapping: dict[str, set[str]]) -> dict[str, set[str]]:
        normalized: dict[str, set[str]] = {}
        for key, values in mapping.items():
            key_norm = key.lower().strip()
            for value in values:
                value_norm = value.lower().strip()
                if not key_norm or not value_norm or key_norm == value_norm:
                    continue
                normalized.setdefault(key_norm, set()).add(value_norm)
                normalized.setdefault(value_norm, set()).add(key_norm)
        return normalized
