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
            "status": self.error_symbol(),
            "id": self.segment_id,
            "offset": self.offset_ms or "",
            "len": self.length_ms or "",
            "dc": "",
            "diff": "",
            "expected": self.expected,
            "heard": "",
        }
