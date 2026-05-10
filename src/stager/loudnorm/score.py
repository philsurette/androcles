
from __future__ import annotations
from dataclasses import dataclass, field

from enum import Enum
import logging
from functools import total_ordering

logger = logging.getLogger(__name__)

@total_ordering
class Score(Enum):
    IDEAL = ("ideal", 1, "\033[92m✓\033[0m")   # ✓
    OK = ("ok", 0, "\u2139")                   # ⓘ
    BAD = ("bad", -1, "\033[93m⚠\033[0m")      # ⚠
    FAIL = ("fail", -2, "\033[91m✗\033[0m")    # ✗

    def __init__(self, value, score, checkmark):
        self._value = value
        self.score = score
        self.checkmark = checkmark

    def __lt__(self, other):
        if not isinstance(other, Score):
            return NotImplemented
        return self.score < other.score
    
    def render(self):
        return self.checkmark