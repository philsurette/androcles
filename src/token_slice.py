#!/usr/bin/env python3
"""Token slice utilities for diff processing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class TokenSlice:
    tokens: list[str]
    types: list[str]
    start: int
    count: int

    def text(self) -> str:
        return "".join(self.tokens[self.start : self.start + self.count])

    def iter_tokens(self) -> Iterable[tuple[str, str]]:
        return zip(
            self.tokens[self.start : self.start + self.count],
            self.types[self.start : self.start + self.count],
        )

    def has_word(self) -> bool:
        for token_type in self.types[self.start : self.start + self.count]:
            if token_type == "word":
                return True
        return False

    def has_hyphen(self, hyphen_chars: set[str]) -> bool:
        for token, token_type in self.iter_tokens():
            if token_type == "punct" and token in hyphen_chars:
                return True
        return False
