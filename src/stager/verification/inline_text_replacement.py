#!/usr/bin/env python3
"""Represent a replacement diff between expected and heard text."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InlineTextReplacement:
    expected: str
    actual: str
    segment_id: str | None = None
