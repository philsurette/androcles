from __future__ import annotations
from dataclasses import dataclass, field
from loudnorm.result import Result

@dataclass 
class Target:
    """
    A target range for an audio measurement.
    """
    too_low: float
    low: float
    high: float
    too_high: float
    target: float # the ideal value

    def __post_init__(self):
        assert self.too_low <= self.low
        assert self.low <= self.high
        assert self.high <= self.too_high

    def check(self, value: float) -> Result:
        if value < self.too_low:
            return Result.TOO_LOW
        elif value < self.low:
            return Result.LOW
        elif value <= self.high:
            return Result.IN_RANGE
        elif value <= self.too_high:
            return Result.HIGH
        else:
            return Result.TOO_HIGH