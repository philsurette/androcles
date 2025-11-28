from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict
from loudnorm.metric import *
from loudnorm.score import Score
from loudnorm.result import Result
from functools import cached_property

@dataclass
class Measurement:
    value: float
    metric: Metric
    normalizable: bool = field(default=True)

    @property
    def result(self) -> Result:
        return self.metric.check(self.value)
    
    @property
    def score(self) -> Score:
        return self.result.score
    
    def as_filter_option(self):
        return f"measured_{self.metric.option}={self.value}"
    
    def render(self)->str:
        r = f"{self.metric.name:>20}: {self.value:>6.1f}{self.result.score.checkmark}"
        if self.result.score != Score.IDEAL:
            r += f" - {self.result.name}"
        return r

class Measurements(dict[str, Measurement]):
    @cached_property
    def score(self) -> Score:
        return min(m.score for m in self.values())
    
    @cached_property
    def normalizable(self) -> bool:
        return min(m.normalizable for m in self.values())
    
    def render(self) -> str:
        r = []
        if not self.normalizable:
            r.append("NOT NORMALIZABLE")
        for m in self.values():
            r.append(f"{m.score.checkmark}{m.metric.abbrev}:{m.value}")
        return ' '.join(r)

class Phase(Enum):
    """
    the loudnorm plugin runs analysis twice... first on the input
    (input phase) - these are the initial values.
    Then on the output - these are the normalized values.
    """
    INPUT = ('measure','Input')
    OUTPUT = ('normalize','Output')

    def __init__(self, value, prefix):
        self._value_ = value
        self.prefix = prefix