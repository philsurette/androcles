#!/usr/bin/env python3
"""Match words or short phrases using CMU pronunciation data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class HomophoneMatcher:
    max_words: int = 2
    _word_cache: dict[str, set[tuple[str, ...]]] = field(default_factory=dict, init=False)
    _phrase_cache: dict[tuple[str, ...], set[tuple[str, ...]]] = field(
        default_factory=dict, init=False
    )
    _cmu_dict: ClassVar[dict[str, list[list[str]]] | None] = None

    def is_homophone(self, expected_words: list[str], actual_words: list[str]) -> bool:
        if not expected_words or not actual_words:
            return False
        if len(expected_words) > self.max_words or len(actual_words) > self.max_words:
            return False
        expected_prons = self._phrase_pronunciations(expected_words)
        if not expected_prons:
            return False
        actual_prons = self._phrase_pronunciations(actual_words)
        if not actual_prons:
            return False
        return not expected_prons.isdisjoint(actual_prons)

    def _phrase_pronunciations(self, words: list[str]) -> set[tuple[str, ...]]:
        key = tuple(words)
        cached = self._phrase_cache.get(key)
        if cached is not None:
            return cached
        combos: list[tuple[str, ...]] = [()]
        for word in words:
            pronunciations = self._word_pronunciations(word)
            if not pronunciations:
                combos = []
                break
            next_combos: list[tuple[str, ...]] = []
            for base in combos:
                for pron in pronunciations:
                    next_combos.append(base + pron)
            combos = next_combos
        result = set(combos)
        self._phrase_cache[key] = result
        return result

    def _word_pronunciations(self, word: str) -> set[tuple[str, ...]]:
        key = word.lower()
        cached = self._word_cache.get(key)
        if cached is not None:
            return cached
        cmu = self._get_cmudict()
        pronunciations = cmu.get(key, [])
        result = {tuple(phones) for phones in pronunciations}
        self._word_cache[key] = result
        return result

    @classmethod
    def _get_cmudict(cls) -> dict[str, list[list[str]]]:
        if cls._cmu_dict is None:
            import cmudict

            cls._cmu_dict = cmudict.dict()
        return cls._cmu_dict
