#!/usr/bin/env python3
"""Generate inline diffs between expected and actual text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from diff_match_patch import diff_match_patch

from inline_text_diff import InlineTextDiff


@dataclass
class InlineTextDiffer:
    window_before: int = 3
    window_after: int = 1
    dmp: diff_match_patch = field(default_factory=diff_match_patch)

    def diff(self, expected: str, actual: str) -> InlineTextDiff:
        diffs, id_to_token, expected_tokens, expected_types, actual_tokens = self._diffs_for_texts(
            expected,
            actual,
        )

        expected_word_indices = self._build_word_indices(expected_types)
        segments, diff_regions = self._build_segments(
            diffs,
            id_to_token,
            expected_tokens,
            actual_tokens,
            expected_word_indices,
        )
        inline_diff = "".join(segment["text"] for segment in segments)
        windowed_diffs = self._build_windowed_diffs(
            segments,
            diff_regions,
            expected_word_indices,
        )
        return InlineTextDiff(
            expected=expected,
            actual=actual,
            inline_diff=inline_diff,
            windowed_diffs=windowed_diffs,
        )

    def count_diffs(self, expected: str, actual: str) -> int:
        diffs, _id_to_token, _expected_tokens, _expected_types, _actual_tokens = self._diffs_for_texts(
            expected,
            actual,
        )
        count = 0
        i = 0
        while i < len(diffs):
            op, _text = diffs[i]
            if op == 0:
                i += 1
                continue
            if op == -1 and i + 1 < len(diffs) and diffs[i + 1][0] == 1:
                count += 1
                i += 2
                continue
            if op == 1 and i + 1 < len(diffs) and diffs[i + 1][0] == -1:
                count += 1
                i += 2
                continue
            count += 1
            i += 1
        return count

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
        return diffs, id_to_token, expected_tokens, expected_types, actual_tokens

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
        if token_type == "space":
            return " "
        return token

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

    def _decode_tokens(self, encoded: str, id_to_token: dict[int, str]) -> list[str]:
        return [id_to_token[ord(ch)] for ch in encoded]

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
        diffs: list[tuple[int, str]],
        id_to_token: dict[int, str],
        expected_tokens: list[str],
        actual_tokens: list[str],
        expected_word_indices: list[int | None],
    ) -> tuple[list[dict], list[tuple[int, int]]]:
        segments: list[dict] = []
        diff_regions: list[tuple[int, int]] = []
        exp_idx = 0
        act_idx = 0
        i = 0
        while i < len(diffs):
            op, text = diffs[i]
            tokens = self._decode_tokens(text, id_to_token)
            count = len(tokens)
            if op == 0:
                for _ in range(count):
                    segments.append(
                        {
                            "text": expected_tokens[exp_idx],
                            "exp_start": exp_idx,
                            "exp_end": exp_idx + 1,
                            "anchor": None,
                        }
                    )
                    exp_idx += 1
                    act_idx += 1
                i += 1
                continue
            if op == -1:
                if i + 1 < len(diffs) and diffs[i + 1][0] == 1:
                    insert_tokens = self._decode_tokens(diffs[i + 1][1], id_to_token)
                    insert_count = len(insert_tokens)
                    expected_text = self._slice_tokens(expected_tokens, exp_idx, count)
                    actual_text = self._slice_tokens(actual_tokens, act_idx, insert_count)
                    segments.append(
                        {
                            "text": self._format_replace(expected_text, actual_text),
                            "exp_start": exp_idx,
                            "exp_end": exp_idx + count,
                            "anchor": None,
                        }
                    )
                    self._add_diff_region(diff_regions, expected_word_indices, exp_idx, exp_idx + count)
                    exp_idx += count
                    act_idx += insert_count
                    i += 2
                    continue
                expected_text = self._slice_tokens(expected_tokens, exp_idx, count)
                segments.append(
                    {
                        "text": self._format_delete(expected_text),
                        "exp_start": exp_idx,
                        "exp_end": exp_idx + count,
                        "anchor": None,
                    }
                )
                self._add_diff_region(diff_regions, expected_word_indices, exp_idx, exp_idx + count)
                exp_idx += count
                i += 1
                continue
            if op == 1:
                if i + 1 < len(diffs) and diffs[i + 1][0] == -1:
                    delete_tokens = self._decode_tokens(diffs[i + 1][1], id_to_token)
                    delete_count = len(delete_tokens)
                    expected_text = self._slice_tokens(expected_tokens, exp_idx, delete_count)
                    actual_text = self._slice_tokens(actual_tokens, act_idx, count)
                    segments.append(
                        {
                            "text": self._format_replace(expected_text, actual_text),
                            "exp_start": exp_idx,
                            "exp_end": exp_idx + delete_count,
                            "anchor": None,
                        }
                    )
                    self._add_diff_region(diff_regions, expected_word_indices, exp_idx, exp_idx + delete_count)
                    exp_idx += delete_count
                    act_idx += count
                    i += 2
                    continue
                actual_text = self._slice_tokens(actual_tokens, act_idx, count)
                anchor = self._anchor_word_index(expected_word_indices, exp_idx)
                segments.append(
                    {
                        "text": self._format_insert(actual_text),
                        "exp_start": exp_idx,
                        "exp_end": exp_idx,
                        "anchor": anchor,
                    }
                )
                if anchor is not None:
                    diff_regions.append((anchor, anchor))
                act_idx += count
                i += 1
                continue
            raise RuntimeError(f"Unexpected diff opcode: {op}")
        return segments, diff_regions

    def _slice_tokens(self, tokens: list[str], start: int, count: int) -> str:
        return "".join(tokens[start : start + count])

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
