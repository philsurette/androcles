#!/usr/bin/env python3
"""Data structures for parsed play text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from abc import ABC

@dataclass
class Title:
    part_no: int
    title: str

@dataclass
class Block(ABC):
    """Base block of play text."""
    part: int | None
    block_no: int
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass
class MetaBlock(Block):
    """Metadata line (::...::)."""
    pass


@dataclass
class DescriptionBlock(Block):
    """Description paragraph ([[...]])."""
    pass


@dataclass
class DirectionBlock(Block):
    """Stage direction paragraph (_..._)."""
    pass


@dataclass
class RoleBlock(Block):
    """Spoken block associated with a role."""
    role: str
    segments: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.role}: {' '.join(self.segments) if self.segments else self.text}"


class PlayText(List[Block]):
    """Container for the ordered blocks of a play."""

    def __init__(self, items: List[Block] | None = None) -> None:
        super().__init__(items or [])
