#!/usr/bin/env python3
"""Dataclass for inline text diffs."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InlineTextDiff:
    expected: str
    actual: str
    inline_diff: str
    windowed_diffs: list[str] = field(default_factory=list)
