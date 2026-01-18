#!/usr/bin/env python3
"""Context for diff processing."""
from __future__ import annotations

from dataclasses import dataclass

from token_slice import TokenSlice


@dataclass
class DiffContext:
    diffs: list[tuple[int, str]]
    id_to_token: dict[int, str]
    expected_tokens: list[str]
    expected_types: list[str]
    actual_tokens: list[str]
    actual_types: list[str]
    expected_word_indices: list[int | None]
    segment_id: str | None = None

    def expected_slice(self, start: int, count: int) -> TokenSlice:
        return TokenSlice(self.expected_tokens, self.expected_types, start, count)

    def actual_slice(self, start: int, count: int) -> TokenSlice:
        return TokenSlice(self.actual_tokens, self.actual_types, start, count)

    def decode(self, encoded: str) -> list[str]:
        return [self.id_to_token[ord(ch)] for ch in encoded]
