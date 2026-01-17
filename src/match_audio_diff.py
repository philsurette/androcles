#!/usr/bin/env python3
"""Diff entry for matched audio segments."""
from __future__ import annotations

from dataclasses import dataclass

from audio_verifier_diff import AudioVerifierDiff


@dataclass
class MatchAudioDiff(AudioVerifierDiff):
    segment_id: str
    expected: str
    heard: str
    diff: str
    match_quality: int

    def error_symbol(self) -> str:
        if self.match_quality == 0:
            return "✅"
        return "⚠️"

    def to_row(self) -> dict[str, object]:
        return {
            "status": self.error_symbol(),
            "id": self.segment_id,
            "offset": self.offset_ms or "",
            "len": self.length_ms or "",
            "dc": self.match_quality,
            "diff": self.diff,
            "expected": self.expected,
            "heard": self.heard,
        }
