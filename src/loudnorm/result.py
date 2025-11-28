from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from loudnorm.score import Score

class Result(Enum):
    TOO_LOW = (-2, Score.BAD)
    LOW = (-1, Score.OK)
    IN_RANGE = (0, Score.IDEAL)
    HIGH = (1, Score.OK)
    TOO_HIGH = (2, Score.BAD)

    def __init__(self, value, score):
        self._value_ = value
        self.score: Score = score