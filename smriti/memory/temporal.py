
"""Half-open valid and transaction intervals for historical memory."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any


def timestamp(value):
    point = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(point, datetime) or point.tzinfo is None or point.utcoffset() is None:
        raise ValueError('Timestamp must be timezone-aware')
    return point.astimezone(timezone.utc)


@dataclass(frozen=True)
class ValidInterval:
    start: datetime
    end: datetime | None = None

    def __post_init__(self):
        object.__setattr__(self, 'start', timestamp(self.start))
        object.__setattr__(self, 'end', timestamp(self.end) if self.end is not None else None)
        if self.end is not None and self.end <= self.start:
            raise ValueError("Interval end must be after start")

    def contains(self, point):
        return self.start <= timestamp(point) and (self.end is None or timestamp(point) < self.end)
# P10.01
@dataclass(frozen=True)
class TransactionInterval(ValidInterval):
    """The period during which Smriti believed a version."""


@dataclass(frozen=True)
class TemporalVersion:
    fact_id: str
    payload: dict[str, Any]
    valid: ValidInterval
    transaction: TransactionInterval
# P10.02

# P10.03

# P10.04
class Timeline:
    """In-memory bitemporal oracle, also used by persistent log replay."""
    def __init__(self, versions=()):
        self.rows = list(versions)

    def valid_at(self, point):
        point = timestamp(point)
        return [v for v in self.rows if v.valid.contains(point)]
# P10.05
    def query(self, valid_at, as_of):
        as_of = timestamp(as_of)
        return [v for v in self.valid_at(valid_at) if v.transaction.contains(as_of)]
# P10.06
