#!/usr/bin/env python3
"""Render a concise audio verification summary for console output."""
from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class AudioVerifierSummaryRenderer:
    format: str = "text"
    window_joiner: str = " | "
    max_windows: int = 3
    include_offsets: bool = True
    include_lengths: bool = True
    _space_re: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._space_re = re.compile(r"\s+")

    def render(self, results: dict) -> str:
        fmt = self.format.lower().strip()
        if fmt == "text":
            return self._render_text(results)
        if fmt == "yaml":
            return self._render_yaml(results)
        raise RuntimeError(f"Unknown summary format: {self.format}")

    def _render_text(self, results: dict) -> str:
        data = self._collect(results)
        lines: list[str] = []
        lines.append(f"Role: {data['role']}")
        lines.append(
            f"Missing: {len(data['missing'])}, Extra: {len(data['extra'])}, Mismatched: {len(data['mismatched'])}"
        )
        if data["missing"]:
            lines.append("Missing:")
            for item in data["missing"]:
                lines.append(f"- {item['segment_id']}: {item['expected']}")
        if data["mismatched"]:
            lines.append("Mismatched:")
            for item in data["mismatched"]:
                timing = self._format_timing(item["offset_ms"], item["length_ms"])
                lines.append(f"- {item['segment_id']}: {item['diff']}{timing}")
        if data["extra"]:
            lines.append("Extra:")
            for item in data["extra"]:
                timing = self._format_timing(item["offset_ms"], item["length_ms"])
                lines.append(f"- {item['heard']}{timing}")
        return "\n".join(lines)

    def _render_yaml(self, results: dict) -> str:
        data = self._collect(results)
        lines: list[str] = []
        lines.append(f"role: {data['role']}")
        lines.append(
            f"counts: {{missing: {len(data['missing'])}, extra: {len(data['extra'])}, mismatched: {len(data['mismatched'])}}}"
        )
        lines.append("missing:")
        if data["missing"]:
            for item in data["missing"]:
                lines.append(f"  - id: {item['segment_id']}")
                lines.append(f"    expected: {item['expected']}")
        else:
            lines.append("  - none")
        lines.append("mismatched:")
        if data["mismatched"]:
            for item in data["mismatched"]:
                lines.append(f"  - id: {item['segment_id']}")
                if item["offset_ms"] is not None:
                    lines.append(f"    offset_ms: {item['offset_ms']}")
                if item["length_ms"] is not None:
                    lines.append(f"    length_ms: {item['length_ms']}")
                lines.append(f"    diff: {item['diff']}")
        else:
            lines.append("  - none")
        lines.append("extra:")
        if data["extra"]:
            for item in data["extra"]:
                lines.append("  -")
                if item["offset_ms"] is not None:
                    lines.append(f"    offset_ms: {item['offset_ms']}")
                if item["length_ms"] is not None:
                    lines.append(f"    length_ms: {item['length_ms']}")
                lines.append(f"    heard: {item['heard']}")
        else:
            lines.append("  - none")
        return "\n".join(lines)

    def _collect(self, results: dict) -> dict[str, object]:
        role = results.get("role")
        if role is None:
            raise RuntimeError("Summary requires role in results")
        segments = results.get("segments")
        if segments is None:
            raise RuntimeError("Summary requires segments in results")
        extra_audio = results.get("extra_audio")
        if extra_audio is None:
            raise RuntimeError("Summary requires extra_audio in results")
        missing: list[dict[str, object]] = []
        mismatched: list[dict[str, object]] = []
        for segment in segments:
            status = segment.get("status")
            segment_id = segment.get("segment_id", "")
            expected = self._compact_text(segment.get("expected_text", ""))
            if status == "missing":
                missing.append(
                    {
                        "segment_id": segment_id,
                        "expected": expected,
                    }
                )
                continue
            if status != "matched":
                raise RuntimeError(f"Unexpected segment status: {status}")
            inline_diff = segment.get("inline_diff", "")
            if inline_diff == segment.get("expected_text", ""):
                continue
            windowed_diffs = segment.get("windowed_diffs") or []
            diff_text = self._format_windows(windowed_diffs, inline_diff)
            offset_ms = self._to_ms(segment.get("matched_audio_start"))
            length_ms = self._length_ms(
                segment.get("matched_audio_start"),
                segment.get("matched_audio_end"),
            )
            mismatched.append(
                {
                    "segment_id": segment_id,
                    "diff": diff_text,
                    "offset_ms": offset_ms,
                    "length_ms": length_ms,
                }
            )
        extra: list[dict[str, object]] = []
        for entry in extra_audio:
            heard = self._compact_text(entry.get("recognized_text", ""))
            offset_ms = self._to_ms(entry.get("matched_audio_start"))
            length_ms = self._length_ms(
                entry.get("matched_audio_start"),
                entry.get("matched_audio_end"),
            )
            extra.append(
                {
                    "heard": heard,
                    "offset_ms": offset_ms,
                    "length_ms": length_ms,
                }
            )
        return {
            "role": role,
            "missing": missing,
            "mismatched": mismatched,
            "extra": extra,
        }

    def _format_windows(self, windowed_diffs: list[str], inline_diff: str) -> str:
        windows = [self._compact_text(text) for text in windowed_diffs if text.strip()]
        if windows:
            if self.max_windows > 0 and len(windows) > self.max_windows:
                windows = windows[: self.max_windows] + ["..."]
            return self.window_joiner.join(windows)
        return self._compact_text(inline_diff)

    def _compact_text(self, text: str) -> str:
        return self._space_re.sub(" ", text).strip()

    def _to_ms(self, seconds: float | None) -> int | None:
        if seconds is None:
            return None
        return int(round(seconds * 1000))

    def _length_ms(self, start: float | None, end: float | None) -> int | None:
        if start is None or end is None:
            return None
        return int(round((end - start) * 1000))

    def _format_timing(self, offset_ms: int | None, length_ms: int | None) -> str:
        parts: list[str] = []
        if self.include_offsets and offset_ms is not None:
            parts.append(f"offset={offset_ms}ms")
        if self.include_lengths and length_ms is not None:
            parts.append(f"len={length_ms}ms")
        if not parts:
            return ""
        return f" ({', '.join(parts)})"
