#!/usr/bin/env python3
"""Diff entry for missing audio segments."""
from __future__ import annotations

from dataclasses import dataclass

from audio_verifier_diff import AudioVerifierDiff


@dataclass
class MissingAudioDiff(AudioVerifierDiff):
    segment_id: str
    expected: str

    def error_symbol(self) -> str:
        return "❌"

    def to_row(self) -> dict[str, object]:
        return {
            "Error": self.error_symbol(),
            "Segment ID": self.segment_id,
            "Offset ms": self.offset_ms or "",
            "Length ms": self.length_ms or "",
            "Expected": self.expected,
            "Heard": "",
            "Diff": "",
            "Match Quality": "",
        }
