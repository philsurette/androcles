#!/usr/bin/env python3
"""Represent a diff event between expected and actual tokens."""
from __future__ import annotations

from dataclasses import dataclass

from token_slice import TokenSlice


@dataclass
class DiffEvent:
    op: str
    expected: TokenSlice | None
    actual: TokenSlice | None
    expected_index: int | None
    actual_index: int | None
