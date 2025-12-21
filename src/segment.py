#!/usr/bin/env python3
"""Segment model objects."""
from __future__ import annotations

from dataclasses import dataclass
from abc import ABC

from segment_id import SegmentId


@dataclass
class Segment(ABC):
    segment_id: SegmentId
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass
class MetaSegment(Segment):
    pass


@dataclass
class DescriptionSegment(Segment):
    pass


@dataclass
class DirectionSegment(Segment):
    pass


@dataclass
class SpeechSegment(Segment):
    role: str

    def __str__(self) -> str:
        return f"{self.role}: {self.text}"


@dataclass
class SimultaneousSegment(Segment):
    """A single line spoken together by multiple roles."""

    roles: list[str]

    def __str__(self) -> str:
        roles = " + ".join(self.roles)
        return f"{roles}: {self.text}"
