
"""Half-open valid and transaction intervals for historical memory."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ValidInterval:
    start: datetime
    end: datetime

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("Interval end must be after start")

    def contains(self, point):
        return self.start <= point < self.end
# P10.01
