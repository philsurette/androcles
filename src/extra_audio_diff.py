#!/usr/bin/env python3
"""Diff entry for extra audio segments."""
from __future__ import annotations

from dataclasses import dataclass

from audio_verifier_diff import AudioVerifierDiff


@dataclass
class ExtraAudioDiff(AudioVerifierDiff):
    heard: str

    def error_symbol(self) -> str:
        return "❌"

    def to_row(self) -> dict[str, object]:
        return {
            "Error": self.error_symbol(),
            "Segment ID": "",
            "Offset ms": self.offset_ms or "",
            "Length ms": self.length_ms or "",
            "Expected": "",
            "Heard": self.heard,
            "Diff": "",
            "Match Quality": "",
        }
