#!/usr/bin/env python3
"""Match words or short phrases using CMU pronunciation data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class HomophoneMatcher:
    max_words: int = 2
    allow_schwa_deletion: bool = True
    schwa_phones: set[str] = field(default_factory=lambda: {"AH0"})
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
        return self._pronunciations_equivalent(expected_prons, actual_prons)

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

    def _pronunciations_equivalent(
        self,
        expected_prons: set[tuple[str, ...]],
        actual_prons: set[tuple[str, ...]],
    ) -> bool:
        if not expected_prons.isdisjoint(actual_prons):
            return True
        if not self.allow_schwa_deletion:
            return False
        expected_stripped = {self._strip_schwa(pron) for pron in expected_prons}
        actual_stripped = {self._strip_schwa(pron) for pron in actual_prons}
        if not expected_stripped.isdisjoint(actual_prons):
            return True
        if not actual_stripped.isdisjoint(expected_prons):
            return True
        return not expected_stripped.isdisjoint(actual_stripped)

    def _strip_schwa(self, pronunciation: tuple[str, ...]) -> tuple[str, ...]:
        if not pronunciation:
            return pronunciation
        return tuple(phone for phone in pronunciation if phone not in self.schwa_phones)

    @classmethod
    def _get_cmudict(cls) -> dict[str, list[list[str]]]:
        if cls._cmu_dict is None:
            import cmudict

            cls._cmu_dict = cmudict.dict()
        return cls._cmu_dict
