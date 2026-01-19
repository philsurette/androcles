#!/usr/bin/env python3
"""Build audio verifier diff entries from alignment output."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time

from audio_verifier_diff import AudioVerifierDiff
from extra_audio_diff import ExtraAudioDiff
from inline_text_differ import InlineTextDiffer
from match_audio_diff import MatchAudioDiff
from missing_audio_diff import MissingAudioDiff
from equivalencies import Equivalencies


@dataclass
class AudioVerifierDiffBuilder:
    window_before: int = 3
    window_after: int = 1
    name_tokens: set[str] = field(default_factory=set)
    equivalencies: Equivalencies | None = None
    homophone_max_words: int = 2
    differ: InlineTextDiffer = field(init=False)
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self.differ = InlineTextDiffer(
            window_before=self.window_before,
            window_after=self.window_after,
            name_tokens=self.name_tokens,
            equivalencies=self.equivalencies,
            homophone_max_words=self.homophone_max_words,
        )

    def build(self, results: dict) -> list[AudioVerifierDiff]:
        start_time = time.perf_counter()
        diff_entries: list[dict[str, object]] = []
        segments = results.get("segments", [])
        prev_offsets, next_offsets = self._segment_anchor_offsets(segments)
        order_index = 0
        for segment in segments:
            status = segment.get("status")
            expected = segment.get("expected_text", "")
            heard = segment.get("matched_audio_text", "")
            segment_id = segment.get("segment_id", "")
            segment_index = segment.get("segment_index")
            offset_ms = self._to_ms(segment.get("matched_audio_start"))
            length_ms = self._length_ms(
                segment.get("matched_audio_start"),
                segment.get("matched_audio_end"),
            )
            if status == "missing":
                diff = MissingAudioDiff(
                    segment_id=segment_id,
                    expected=expected,
                    offset_ms=offset_ms,
                    length_ms=length_ms,
                )
                anchor = self._missing_anchor(
                    segment_index,
                    prev_offsets,
                    next_offsets,
                )
                diff_entries.append(
                    {
                        "diff": diff,
                        "anchor": anchor,
                        "order": order_index,
                    }
                )
                order_index += 1
                continue
            if status == "matched":
                inline_diff = segment.get("inline_diff")
                if inline_diff is None:
                    inline_diff = self.differ.diff(
                        expected,
                        heard,
                        segment_id=segment_id,
                    ).inline_diff
                match_quality = self.differ.count_diffs(
                    expected,
                    heard,
                    segment_id=segment_id,
                )
                diff = MatchAudioDiff(
                    segment_id=segment_id,
                    expected=expected,
                    heard=heard,
                    diff=inline_diff,
                    match_quality=match_quality,
                    offset_ms=offset_ms,
                    length_ms=length_ms,
                )
                diff_entries.append(
                    {
                        "diff": diff,
                        "anchor": offset_ms,
                        "order": order_index,
                    }
                )
                order_index += 1
                continue
            raise RuntimeError(f"Unexpected segment status: {status}")

        extra_audio = results.get("extra_audio", [])
        for entry in extra_audio:
            heard = entry.get("recognized_text", "")
            offset_ms = self._to_ms(entry.get("matched_audio_start"))
            length_ms = self._length_ms(
                entry.get("matched_audio_start"),
                entry.get("matched_audio_end"),
            )
            diff = ExtraAudioDiff(
                heard=heard,
                offset_ms=offset_ms,
                length_ms=length_ms,
            )
            diff_entries.append(
                {
                    "diff": diff,
                    "anchor": offset_ms,
                    "order": order_index,
                }
            )
            order_index += 1

        diffs = self._sort_by_audio_position(diff_entries)
        elapsed = time.perf_counter() - start_time
        self._logger.info("Built %d diff rows in %.2fs", len(diffs), elapsed)
        return diffs

    def _to_ms(self, seconds: float | None) -> int | None:
        if seconds is None:
            return None
        return int(round(seconds * 1000))

    def _length_ms(self, start: float | None, end: float | None) -> int | None:
        if start is None or end is None:
            return None
        return int(round((end - start) * 1000))

    def _sort_by_audio_position(self, diffs: list[dict[str, object]]) -> list[AudioVerifierDiff]:
        diffs.sort(key=self._sort_key)
        return [entry["diff"] for entry in diffs]

    def _sort_key(self, entry: dict[str, object]) -> tuple[bool, int, int]:
        anchor = entry.get("anchor")
        order = entry.get("order", 0)
        if anchor is None:
            return (True, 0, order)
        return (False, int(anchor), order)

    def _segment_anchor_offsets(
        self,
        segments: list[dict],
    ) -> tuple[list[int | None], list[int | None]]:
        if not segments:
            return [], []
        count = max(seg.get("segment_index", 0) for seg in segments) + 1
        ordered: list[dict | None] = [None] * count
        for segment in segments:
            ordered[segment.get("segment_index")] = segment
        prev_offsets: list[int | None] = [None] * count
        next_offsets: list[int | None] = [None] * count
        last_offset: int | None = None
        for idx in range(count):
            segment = ordered[idx]
            if segment is None:
                prev_offsets[idx] = last_offset
                continue
            offset = self._to_ms(segment.get("matched_audio_start"))
            prev_offsets[idx] = last_offset
            if offset is not None:
                last_offset = offset
        next_offset: int | None = None
        for idx in range(count - 1, -1, -1):
            segment = ordered[idx]
            if segment is None:
                next_offsets[idx] = next_offset
                continue
            offset = self._to_ms(segment.get("matched_audio_start"))
            next_offsets[idx] = next_offset
            if offset is not None:
                next_offset = offset
        return prev_offsets, next_offsets

    def _missing_anchor(
        self,
        segment_index: int | None,
        prev_offsets: list[int | None],
        next_offsets: list[int | None],
    ) -> int | None:
        if segment_index is None:
            return None
        if segment_index < 0 or segment_index >= len(prev_offsets):
            return None
        prev_offset = prev_offsets[segment_index]
        next_offset = next_offsets[segment_index]
        if prev_offset is None and next_offset is None:
            return -(segment_index + 1)
        if prev_offset is None:
            return -(segment_index + 1)
        if next_offset is None:
            return prev_offset + 1
        return int(round((prev_offset + next_offset) / 2))
