#!/usr/bin/env python3
"""Base class for audio verifier diff rows."""
from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class AudioVerifierDiff(ABC):
    offset_ms: int | None
    length_ms: int | None

    @abstractmethod
    def error_symbol(self) -> str:
        raise RuntimeError("not implemented")

    @abstractmethod
    def to_row(self) -> dict[str, object]:
        raise RuntimeError("not implemented")
