#!/usr/bin/env python3
"""Compare token slices with punctuation, spelling, and equivalency rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar
import re

from rapidfuzz import fuzz

from spelling_normalizer import SpellingNormalizer
from equivalencies import Equivalencies
from token_slice import TokenSlice


@dataclass
class TokenComparator:
    ignorable_punct: set[str]
    hyphen_chars: set[str]
    name_tokens: set[str] = field(default_factory=set)
    name_similarity: float = 0.85
    spelling_normalizer: SpellingNormalizer | None = None
    equivalencies: Equivalencies | None = None
    number_re: ClassVar[re.Pattern[str]] = re.compile(r"^(\d+)(?:st|nd|rd|th)?$")
    roman_re: ClassVar[re.Pattern[str]] = re.compile(r"^[ivxlcdm]+$")
    roman_values: ClassVar[dict[str, int]] = {
        "i": 1,
        "v": 5,
        "x": 10,
        "l": 50,
        "c": 100,
        "d": 500,
        "m": 1000,
    }
    number_words: ClassVar[dict[str, int]] = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
    }
    ordinal_words: ClassVar[dict[str, int]] = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10,
        "eleventh": 11,
        "twelfth": 12,
        "thirteenth": 13,
        "fourteenth": 14,
        "fifteenth": 15,
        "sixteenth": 16,
        "seventeenth": 17,
        "eighteenth": 18,
        "nineteenth": 19,
        "twentieth": 20,
        "thirtieth": 30,
        "fortieth": 40,
        "fiftieth": 50,
        "sixtieth": 60,
        "seventieth": 70,
        "eightieth": 80,
        "ninetieth": 90,
    }
    scale_words: ClassVar[dict[str, int]] = {
        "hundred": 100,
        "thousand": 1000,
    }

    def normalize_token(self, token: str, token_type: str) -> str:
        if token_type == "space":
            return " "
        if token_type == "word":
            token = token.lower()
            token = token.replace("\u2019", "'").replace("\u2018", "'")
            token = token.replace("'", "")
            normalized_number = self._normalize_number_token(token)
            return normalized_number if normalized_number is not None else token
        return token

    def is_ignorable(self, token_slice: TokenSlice) -> bool:
        has_ignorable = False
        for token, token_type in token_slice.iter_tokens():
            if token_type == "space":
                has_ignorable = True
                continue
            if token_type == "punct" and token in self.ignorable_punct:
                has_ignorable = True
                continue
            return False
        return has_ignorable

    def normalized_words(self, token_slice: TokenSlice) -> list[str]:
        words: list[str] = []
        for token, token_type in token_slice.iter_tokens():
            if token_type != "word":
                continue
            word = token.lower().replace("\u2019", "'").replace("\u2018", "'")
            word = word.replace("'", "")
            roman_value = self._roman_to_int(word)
            if roman_value is not None:
                words.append(str(roman_value))
                continue
            digit_match = self.number_re.match(word)
            if digit_match:
                words.append(digit_match.group(1))
                continue
            words.append(word)
        return self._coalesce_number_words(words)

    def raw_words(self, token_slice: TokenSlice) -> list[str]:
        words: list[str] = []
        for token, token_type in token_slice.iter_tokens():
            if token_type != "word":
                continue
            word = token.lower().replace("\u2019", "'").replace("\u2018", "'")
            word = word.replace("'", "")
            if word:
                words.append(word)
        return words

    def slices_equivalent(
        self,
        expected_slice: TokenSlice,
        actual_slice: TokenSlice,
        segment_id: str | None,
    ) -> bool:
        expected_words = self.normalized_words(expected_slice)
        actual_words = self.normalized_words(actual_slice)
        if expected_words == actual_words:
            return True
        if expected_words and actual_words and self._equivalencies_match(
            expected_words,
            actual_words,
            segment_id,
        ):
            return True
        if expected_words and actual_words and self._hyphen_join_equivalent(
            expected_slice,
            actual_slice,
            expected_words,
            actual_words,
        ):
            return True
        if expected_words and actual_words and self._joined_word_equivalent(
            expected_slice,
            actual_slice,
        ):
            return True
        if not expected_words or not actual_words:
            return False
        if len(expected_words) == len(actual_words):
            for expected_word, actual_word in zip(expected_words, actual_words):
                if expected_word == actual_word:
                    continue
                if self._equivalencies_word_match(expected_word, actual_word, segment_id):
                    continue
                if self._name_match(expected_word, actual_word):
                    continue
                if self._spelling_equivalent(expected_word, actual_word):
                    continue
                return False
            return True
        if self._all_name_words(expected_words):
            ratio = fuzz.ratio("".join(expected_words), "".join(actual_words)) / 100.0
            return ratio >= self.name_similarity
        return False

    def _name_match(self, expected_word: str, actual_word: str) -> bool:
        if expected_word not in self.name_tokens:
            return False
        ratio = fuzz.ratio(expected_word, actual_word) / 100.0
        return ratio >= self.name_similarity

    def _all_name_words(self, words: list[str]) -> bool:
        if not words:
            return False
        return all(word in self.name_tokens for word in words)

    def _spelling_equivalent(self, expected_word: str, actual_word: str) -> bool:
        if expected_word == actual_word:
            return True
        if self.spelling_normalizer is None:
            self.spelling_normalizer = SpellingNormalizer.from_breame()
        return self.spelling_normalizer.is_equivalent(expected_word, actual_word)

    def _equivalencies_match(
        self,
        expected_words: list[str],
        actual_words: list[str],
        segment_id: str | None,
    ) -> bool:
        if self.equivalencies is None:
            return False
        expected_phrase = " ".join(expected_words)
        actual_phrase = " ".join(actual_words)
        return self.equivalencies.is_equivalent(
            expected_phrase,
            actual_phrase,
            segment_id=segment_id,
        )

    def _equivalencies_word_match(
        self,
        expected_word: str,
        actual_word: str,
        segment_id: str | None,
    ) -> bool:
        if self.equivalencies is None:
            return False
        return self.equivalencies.is_equivalent(
            expected_word,
            actual_word,
            segment_id=segment_id,
        )

    def _hyphen_join_equivalent(
        self,
        expected_slice: TokenSlice,
        actual_slice: TokenSlice,
        expected_words: list[str],
        actual_words: list[str],
    ) -> bool:
        if not expected_slice.has_hyphen(self.hyphen_chars) and not actual_slice.has_hyphen(
            self.hyphen_chars
        ):
            return False
        return "".join(expected_words) == "".join(actual_words)

    def _normalize_number_token(self, token: str) -> str | None:
        match = self.number_re.match(token)
        if match:
            return match.group(1)
        roman_value = self._roman_to_int(token)
        if roman_value is not None:
            return str(roman_value)
        if token in self.ordinal_words:
            return str(self.ordinal_words[token])
        if token in self.number_words:
            return str(self.number_words[token])
        return None

    def _coalesce_number_words(self, words: list[str]) -> list[str]:
        if not words:
            return []
        normalized: list[str] = []
        idx = 0
        while idx < len(words):
            value, consumed = self._parse_number_sequence(words, idx)
            if consumed:
                normalized.append(str(value))
                idx += consumed
                continue
            normalized.append(words[idx])
            idx += 1
        return normalized

    def _parse_number_sequence(self, words: list[str], start: int) -> tuple[int | None, int]:
        total = 0
        current = 0
        consumed = 0
        idx = start
        saw_number = False
        while idx < len(words):
            word = words[idx]
            if word == "and":
                if not saw_number:
                    break
                consumed += 1
                idx += 1
                continue
            digit_match = self.number_re.match(word)
            if digit_match:
                if saw_number:
                    break
                return int(digit_match.group(1)), 1
            roman_value = self._roman_to_int(word)
            if roman_value is not None:
                if saw_number:
                    break
                return roman_value, 1
            if word in self.ordinal_words:
                current += self.ordinal_words[word]
                consumed += 1
                saw_number = True
                break
            if word in self.number_words:
                current += self.number_words[word]
                consumed += 1
                saw_number = True
                idx += 1
                continue
            if word in self.scale_words:
                scale = self.scale_words[word]
                current = current or 1
                current *= scale
                if scale >= 1000:
                    total += current
                    current = 0
                consumed += 1
                saw_number = True
                idx += 1
                continue
            break
        if not saw_number:
            return None, 0
        total += current
        return total, consumed

    def _roman_to_int(self, token: str) -> int | None:
        if not token or not self.roman_re.match(token):
            return None
        total = 0
        prev = 0
        for char in reversed(token):
            value = self.roman_values.get(char)
            if value is None:
                return None
            if value < prev:
                total -= value
            else:
                total += value
                prev = value
        if total < 1 or total > 100:
            return None
        if self._int_to_roman(total) != token:
            return None
        return total

    def _int_to_roman(self, value: int) -> str:
        mapping = [
            (100, "c"),
            (90, "xc"),
            (50, "l"),
            (40, "xl"),
            (10, "x"),
            (9, "ix"),
            (5, "v"),
            (4, "iv"),
            (1, "i"),
        ]
        result = []
        remaining = value
        for number, numeral in mapping:
            while remaining >= number:
                result.append(numeral)
                remaining -= number
        return "".join(result)

    def _joined_word_equivalent(
        self,
        expected_slice: TokenSlice,
        actual_slice: TokenSlice,
    ) -> bool:
        expected_words = self.raw_words(expected_slice)
        actual_words = self.raw_words(actual_slice)
        if len(expected_words) == 1 and len(actual_words) == 2:
            return expected_words[0] == "".join(actual_words)
        if len(actual_words) == 1 and len(expected_words) == 2:
            return actual_words[0] == "".join(expected_words)
        return False
