from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecordingContext:
    speaker: str
    text: str
