#!/usr/bin/env python3
"""Generate inline diffs between expected and actual text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
import string

from diff_match_patch import diff_match_patch

from diff_context import DiffContext
from diff_walker import DiffWalker
from inline_text_diff import InlineTextDiff
from inline_text_replacement import InlineTextReplacement
from token_comparator import TokenComparator
from token_slice import TokenSlice
from spelling_normalizer import SpellingNormalizer
from equivalencies import Equivalencies


@dataclass
class InlineTextDiffer:
    window_before: int = 3
    window_after: int = 1
    dmp: diff_match_patch = field(default_factory=diff_match_patch)
    ignorable_punct: set[str] = field(
        default_factory=lambda: set(string.punctuation)
        | {"\u201c", "\u201d", "\u2018", "\u2019", "\u2026", "\u2014", "\u2013"}
    )
    name_tokens: set[str] = field(default_factory=set)
    name_similarity: float = 0.85
    spelling_normalizer: SpellingNormalizer | None = None
    equivalencies: Equivalencies | None = None

    _hyphen_chars: set[str] = field(
        default_factory=lambda: {"-", "\u2014", "\u2013"},
        init=False,
        repr=False,
    )
    _comparator: TokenComparator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._comparator = TokenComparator(
            ignorable_punct=self.ignorable_punct,
            hyphen_chars=self._hyphen_chars,
            name_tokens=self.name_tokens,
            name_similarity=self.name_similarity,
            spelling_normalizer=self.spelling_normalizer,
            equivalencies=self.equivalencies,
        )

    def diff(self, expected: str, actual: str, segment_id: str | None = None) -> InlineTextDiff:
        context = self._build_context(expected, actual, segment_id)
        segments, diff_regions = self._build_segments(context)
        inline_diff = "".join(segment["text"] for segment in segments)
        windowed_diffs = self._build_windowed_diffs(
            segments,
            diff_regions,
            context.expected_word_indices,
        )
        return InlineTextDiff(
            expected=expected,
            actual=actual,
            inline_diff=inline_diff,
            windowed_diffs=windowed_diffs,
        )

    def count_diffs(self, expected: str, actual: str, segment_id: str | None = None) -> int:
        context = self._build_context(expected, actual, segment_id)
        count = 0
        for event in DiffWalker(context):
            if event.op == "match":
                continue
            if event.op == "replace":
                if self._ignore_replacement(event.expected, event.actual, context.segment_id):
                    continue
                count += 1
                continue
            if event.op == "delete":
                if event.expected is None:
                    raise RuntimeError("Delete event missing expected slice")
                if self._comparator.is_ignorable(event.expected):
                    continue
                count += 1
                continue
            if event.op == "insert":
                if event.actual is None:
                    raise RuntimeError("Insert event missing actual slice")
                if self._comparator.is_ignorable(event.actual):
                    continue
                count += 1
                continue
            raise RuntimeError(f"Unexpected diff event: {event.op}")
        return count

    def replacement_pairs(
        self,
        expected: str,
        actual: str,
        segment_id: str | None = None,
    ) -> list[InlineTextReplacement]:
        context = self._build_context(expected, actual, segment_id)
        replacements: list[InlineTextReplacement] = []
        for event in DiffWalker(context):
            if event.op != "replace":
                continue
            if self._ignore_replacement(event.expected, event.actual, context.segment_id):
                continue
            if event.expected is None or event.actual is None:
                raise RuntimeError("Replace event missing expected or actual slice")
            if not event.expected.has_word() or not event.actual.has_word():
                continue
            expected_text = event.expected.text().strip()
            actual_text = event.actual.text().strip()
            if expected_text and actual_text:
                replacements.append(
                    InlineTextReplacement(
                        expected=expected_text,
                        actual=actual_text,
                        segment_id=context.segment_id,
                    )
                )
        return replacements

    def _build_context(
        self,
        expected: str,
        actual: str,
        segment_id: str | None,
    ) -> DiffContext:
        diffs, id_to_token, expected_tokens, expected_types, actual_tokens, actual_types = self._diffs_for_texts(
            expected,
            actual,
        )
        expected_word_indices = self._build_word_indices(expected_types)
        return DiffContext(
            diffs=diffs,
            id_to_token=id_to_token,
            expected_tokens=expected_tokens,
            expected_types=expected_types,
            actual_tokens=actual_tokens,
            actual_types=actual_types,
            expected_word_indices=expected_word_indices,
            segment_id=segment_id,
        )

    def _diffs_for_texts(
        self,
        expected: str,
        actual: str,
    ) -> tuple[
        list[tuple[int, str]],
        dict[int, str],
        list[str],
        list[str],
        list[str],
        list[str],
    ]:
        expected_tokens, expected_types = self._tokenize(expected)
        actual_tokens, actual_types = self._tokenize(actual)
        expected_norm = [
            self._normalize_token(token, token_type)
            for token, token_type in zip(expected_tokens, expected_types)
        ]
        actual_norm = [
            self._normalize_token(token, token_type)
            for token, token_type in zip(actual_tokens, actual_types)
        ]
        encoded_expected, encoded_actual, id_to_token = self._encode_tokens(
            expected_norm,
            actual_norm,
        )
        diffs = self.dmp.diff_main(encoded_expected, encoded_actual)
        self.dmp.diff_cleanupSemantic(diffs)
        return diffs, id_to_token, expected_tokens, expected_types, actual_tokens, actual_types

    def _tokenize(self, text: str) -> tuple[list[str], list[str]]:
        tokens: list[str] = []
        types: list[str] = []
        current = ""
        current_type = ""
        for char in text:
            if char.isspace():
                token_type = "space"
            elif self._is_word_char(char):
                token_type = "word"
            else:
                token_type = "punct"
            if token_type == "punct":
                if current:
                    tokens.append(current)
                    types.append(current_type)
                    current = ""
                    current_type = ""
                tokens.append(char)
                types.append(token_type)
                continue
            if token_type == current_type:
                current += char
            else:
                if current:
                    tokens.append(current)
                    types.append(current_type)
                current = char
                current_type = token_type
        if current:
            tokens.append(current)
            types.append(current_type)
        return tokens, types

    def _is_word_char(self, char: str) -> bool:
        return char.isalnum() or char in ("'", "\u2019", "_")

    def _normalize_token(self, token: str, token_type: str) -> str:
        return self._comparator.normalize_token(token, token_type)

    def _encode_tokens(
        self,
        expected_tokens: Iterable[str],
        actual_tokens: Iterable[str],
    ) -> tuple[str, str, dict[int, str]]:
        token_map: dict[str, int] = {}
        encoded_expected = self._encode_stream(expected_tokens, token_map)
        encoded_actual = self._encode_stream(actual_tokens, token_map)
        id_to_token = {value: token for token, value in token_map.items()}
        return encoded_expected, encoded_actual, id_to_token

    def _encode_stream(self, tokens: Iterable[str], token_map: dict[str, int]) -> str:
        encoded = []
        for token in tokens:
            if token not in token_map:
                token_map[token] = len(token_map) + 1
            encoded.append(chr(token_map[token]))
        return "".join(encoded)

    def _build_word_indices(self, token_types: list[str]) -> list[int | None]:
        word_index = 0
        indices: list[int | None] = []
        for token_type in token_types:
            if token_type == "word":
                indices.append(word_index)
                word_index += 1
            else:
                indices.append(None)
        return indices

    def _build_segments(
        self,
        context: DiffContext,
    ) -> tuple[list[dict], list[tuple[int, int]]]:
        segments: list[dict] = []
        diff_regions: list[tuple[int, int]] = []
        for event in DiffWalker(context):
            if event.op == "match":
                if event.expected is None:
                    raise RuntimeError("Match event missing expected slice")
                self._append_match_segments(segments, event.expected)
                continue
            if event.op == "replace":
                if event.expected is None or event.actual is None:
                    raise RuntimeError("Replace event missing expected or actual slice")
                if self._ignore_replacement(event.expected, event.actual, context.segment_id):
                    expected_text = event.expected.text()
                    segments.append(
                        {
                            "text": expected_text,
                            "exp_start": event.expected.start,
                            "exp_end": event.expected.start + event.expected.count,
                            "anchor": None,
                        }
                    )
                    continue
                expected_text = event.expected.text()
                actual_text = event.actual.text()
                segments.append(
                    {
                        "text": self._format_replace(expected_text, actual_text),
                        "exp_start": event.expected.start,
                        "exp_end": event.expected.start + event.expected.count,
                        "anchor": None,
                    }
                )
                self._add_diff_region(
                    diff_regions,
                    context.expected_word_indices,
                    event.expected.start,
                    event.expected.start + event.expected.count,
                )
                continue
            if event.op == "delete":
                if event.expected is None:
                    raise RuntimeError("Delete event missing expected slice")
                expected_text = event.expected.text()
                if self._comparator.is_ignorable(event.expected):
                    segments.append(
                        {
                            "text": expected_text,
                            "exp_start": event.expected.start,
                            "exp_end": event.expected.start + event.expected.count,
                            "anchor": None,
                        }
                    )
                    continue
                segments.append(
                    {
                        "text": self._format_delete(expected_text),
                        "exp_start": event.expected.start,
                        "exp_end": event.expected.start + event.expected.count,
                        "anchor": None,
                    }
                )
                self._add_diff_region(
                    diff_regions,
                    context.expected_word_indices,
                    event.expected.start,
                    event.expected.start + event.expected.count,
                )
                continue
            if event.op == "insert":
                if event.actual is None:
                    raise RuntimeError("Insert event missing actual slice")
                if self._comparator.is_ignorable(event.actual):
                    continue
                if event.expected_index is None:
                    raise RuntimeError("Insert event missing expected index")
                actual_text = event.actual.text()
                anchor = self._anchor_word_index(
                    context.expected_word_indices,
                    event.expected_index,
                )
                segments.append(
                    {
                        "text": self._format_insert(actual_text),
                        "exp_start": event.expected_index,
                        "exp_end": event.expected_index,
                        "anchor": anchor,
                    }
                )
                if anchor is not None:
                    diff_regions.append((anchor, anchor))
                continue
            raise RuntimeError(f"Unexpected diff event: {event.op}")
        return segments, diff_regions

    def _append_match_segments(self, segments: list[dict], token_slice: TokenSlice) -> None:
        for offset in range(token_slice.count):
            idx = token_slice.start + offset
            segments.append(
                {
                    "text": token_slice.tokens[idx],
                    "exp_start": idx,
                    "exp_end": idx + 1,
                    "anchor": None,
                }
            )

    def _ignore_replacement(
        self,
        expected_slice: TokenSlice | None,
        actual_slice: TokenSlice | None,
        segment_id: str | None,
    ) -> bool:
        if expected_slice is None or actual_slice is None:
            return False
        if self._comparator.slices_equivalent(expected_slice, actual_slice, segment_id):
            return True
        return self._comparator.is_ignorable(expected_slice) and self._comparator.is_ignorable(actual_slice)

    def _format_replace(self, expected_text: str, actual_text: str) -> str:
        lead, expected_core, trail = self._split_whitespace(expected_text)
        _, actual_core, _ = self._split_whitespace(actual_text)
        if not expected_core and not actual_core:
            return expected_text
        if not expected_core:
            return lead + f"[+{actual_core}+]" + trail
        if not actual_core:
            return lead + f"[-{expected_core}-]" + trail
        return lead + f"[{actual_core}/{expected_core}]" + trail

    def _format_delete(self, expected_text: str) -> str:
        lead, core, trail = self._split_whitespace(expected_text)
        if not core:
            return expected_text
        return lead + f"[-{core}-]" + trail

    def _format_insert(self, actual_text: str) -> str:
        lead, core, trail = self._split_whitespace(actual_text)
        if not core:
            return actual_text
        return lead + f"[+{core}+]" + trail

    def _split_whitespace(self, text: str) -> tuple[str, str, str]:
        leading = ""
        trailing = ""
        idx = 0
        while idx < len(text) and text[idx].isspace():
            leading += text[idx]
            idx += 1
        end_idx = len(text)
        while end_idx > idx and text[end_idx - 1].isspace():
            trailing = text[end_idx - 1] + trailing
            end_idx -= 1
        core = text[idx:end_idx]
        return leading, core, trailing

    def _add_diff_region(
        self,
        diff_regions: list[tuple[int, int]],
        expected_word_indices: list[int | None],
        start: int,
        end: int,
    ) -> None:
        word_range = self._word_range_for_tokens(expected_word_indices, start, end)
        if word_range is not None:
            diff_regions.append(word_range)

    def _word_range_for_tokens(
        self,
        expected_word_indices: list[int | None],
        start: int,
        end: int,
    ) -> tuple[int, int] | None:
        word_indices = [idx for idx in expected_word_indices[start:end] if idx is not None]
        if not word_indices:
            return None
        return min(word_indices), max(word_indices)

    def _anchor_word_index(self, expected_word_indices: list[int | None], exp_idx: int) -> int | None:
        for idx in range(exp_idx - 1, -1, -1):
            if expected_word_indices[idx] is not None:
                return expected_word_indices[idx]
        for idx in range(exp_idx, len(expected_word_indices)):
            if expected_word_indices[idx] is not None:
                return expected_word_indices[idx]
        return None

    def _build_windowed_diffs(
        self,
        segments: list[dict],
        diff_regions: list[tuple[int, int]],
        expected_word_indices: list[int | None],
    ) -> list[str]:
        word_count = self._word_count(expected_word_indices)
        if word_count == 0:
            return []
        windows = self._expand_windows(diff_regions, word_count)
        merged = self._merge_windows(windows)
        windowed_diffs: list[str] = []
        for window_start, window_end in merged:
            token_start, token_end = self._token_range_for_window(
                expected_word_indices, window_start, window_end
            )
            parts: list[str] = []
            for segment in segments:
                if self._segment_in_window(segment, token_start, token_end, window_start, window_end):
                    parts.append(segment["text"])
            window_text = "".join(parts).strip()
            if window_text:
                windowed_diffs.append(window_text)
        return windowed_diffs

    def _word_count(self, expected_word_indices: list[int | None]) -> int:
        count = 0
        for idx in expected_word_indices:
            if idx is not None:
                count = idx + 1
        return count

    def _expand_windows(self, diff_regions: list[tuple[int, int]], word_count: int) -> list[tuple[int, int]]:
        windows: list[tuple[int, int]] = []
        for start, end in diff_regions:
            window_start = max(0, start - self.window_before)
            window_end = min(word_count - 1, end + self.window_after)
            windows.append((window_start, window_end))
        return windows

    def _merge_windows(self, windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not windows:
            return []
        windows.sort()
        merged = [windows[0]]
        for start, end in windows[1:]:
            prev_start, prev_end = merged[-1]
            if start <= prev_end + 1:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))
        return merged

    def _token_range_for_window(
        self,
        expected_word_indices: list[int | None],
        window_start: int,
        window_end: int,
    ) -> tuple[int, int]:
        token_start = None
        token_end = None
        for idx, word_idx in enumerate(expected_word_indices):
            if word_idx is None:
                continue
            if token_start is None and word_idx >= window_start:
                token_start = idx
            if word_idx <= window_end:
                token_end = idx + 1
        if token_start is None or token_end is None:
            return 0, 0
        return token_start, token_end

    def _segment_in_window(
        self,
        segment: dict,
        token_start: int,
        token_end: int,
        window_start: int,
        window_end: int,
    ) -> bool:
        if segment["exp_end"] > token_start and segment["exp_start"] < token_end:
            return True
        anchor = segment.get("anchor")
        if anchor is not None and window_start <= anchor <= window_end:
            return True
        return False
