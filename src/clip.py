#!/usr/bin/env python3
"""Clip definitions for audio plan items."""
from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
import os

import paths


PROJECT_ROOT = paths.ROOT.parent


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


@dataclass
class Clip(ABC):
    path: Path | None
    text: str | None
    role: str | None
    clip_id: str | None
    length_ms: int
    offset_ms: int = field(default=0)

    @property
    @abstractmethod
    def kind(self) -> str:
        ...


@dataclass
class CalloutClip(Clip):
    @property
    def kind(self) -> str:
        return "callout"

    def __str__(self) -> str:
        if self.path is None:
            raise RuntimeError(f"callout missing: {self.path}")
        rel = _rel_path(self.path)
        return f"{rel}: {self.clip_id}"


@dataclass
class SegmentClip(Clip):
    @property
    def kind(self) -> str:
        return "segment"

    def __str__(self) -> str:
        if self.path is None:
            raise RuntimeError(f"segment missing: {self.path}")
        rel = _rel_path(self.path)
        clip_id = f"{self.clip_id}:" if self.clip_id is not None else ''
        role = f"{self.role} - " if self.role is not None else ''
        return f"{rel}: {clip_id}{role}{self.text}"


@dataclass
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


@dataclass
class ParallelClips:
    """Container for clips that should play at the same offset."""

    clips: list[Clip]
    offset_ms: int = 0
    length_ms: int = 0

    @property
    def kind(self) -> str:
        return "parallel"

    def __str__(self) -> str:
        clip_str = " | ".join(str(c) for c in self.clips)
        return f"[parallel] {clip_str}"
