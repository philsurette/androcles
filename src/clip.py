#!/usr/bin/env python3
"""Clip definitions for audio plan items."""
from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
import os

from paths import AUDIO_OUT_DIR, ROOT


PROJECT_ROOT = ROOT.parent


def _rel_path(path: Path) -> Path:
    """Return path relative to project root when possible."""
    base = PROJECT_ROOT
    if hasattr(Path, "is_relative_to"):
        try:
            if path.is_relative_to(base):
                return path.relative_to(base)
        except Exception:
            pass
    try:
        return path.relative_to(base)
    except ValueError:
        return Path(os.path.relpath(path, base))


@dataclass(frozen=True)
class Clip(ABC):
    path: Path | None
    text: str | None
    role: str | None
    clip_id: str | None
    length_ms: int
    offset_ms: int

    @property
    @abstractmethod
    def kind(self) -> str:
        ...


@dataclass(frozen=True)
class CalloutClip(Clip):
    @property
    def kind(self) -> str:
        return "callout"

    def __str__(self) -> str:
        if self.path is None:
            return "[callout missing]"
        rel = _rel_path(self.path)
        return f"{rel}: {self.clip_id}"


@dataclass(frozen=True)
class SegmentClip(Clip):
    @property
    def kind(self) -> str:
        return "segment"

    def __str__(self) -> str:
        if self.path is None:
            return "[segment missing]"
        rel = _rel_path(self.path)
        return f"{rel}: {self.clip_id}:{self.role} - {self.text}"


@dataclass(frozen=True)
class Silence(Clip):
    def __init__(self, length_ms: int, offset_ms: int = 0):
        object.__setattr__(self, "length_ms", length_ms)
        object.__setattr__(self, "offset_ms", offset_ms)
        object.__setattr__(self, "path", None)
        object.__setattr__(self, "text", None)
        object.__setattr__(self, "role", None)
        object.__setattr__(self, "clip_id", None)

    @property
    def kind(self) -> str:
        return "silence"

    def __str__(self) -> str:
        return f"[silence {self.length_ms}ms]"
