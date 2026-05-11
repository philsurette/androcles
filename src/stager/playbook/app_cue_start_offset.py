from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppCueStartOffset:
    requested_window_ms: int
    start_ms: int
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_window_ms": self.requested_window_ms,
            "start_ms": self.start_ms,
            "confidence": self.confidence,
        }
