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
            "Error": self.error_symbol(),
            "Segment ID": self.segment_id,
            "Offset ms": self.offset_ms or "",
            "Length ms": self.length_ms or "",
            "Expected": self.expected,
            "Heard": self.heard,
            "Diff": self.diff,
            "Match Quality": self.match_quality,
        }
