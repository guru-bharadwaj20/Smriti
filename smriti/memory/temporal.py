
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
    def correct(self, fact_id, payload, valid, recorded_at):
        """Correct the overlap, retaining both old beliefs and unaffected times."""
        recorded_at = timestamp(recorded_at)
        additions = []
        rows = []
        for old in self.rows:
            overlap = (old.valid.end is None or valid.start < old.valid.end) and (valid.end is None or old.valid.start < valid.end)
            if old.fact_id != fact_id or old.transaction.end is not None or not overlap:
                rows.append(old)
                continue
            if recorded_at <= old.transaction.start:
                raise ValueError("Corrections must advance transaction time")
            rows.append(replace(old, transaction=TransactionInterval(old.transaction.start, recorded_at)))
            if old.valid.start < valid.start:
                additions.append(TemporalVersion(fact_id, dict(old.payload), ValidInterval(old.valid.start, valid.start), TransactionInterval(recorded_at)))
            if valid.end is not None and (old.valid.end is None or valid.end < old.valid.end):
                additions.append(TemporalVersion(fact_id, dict(old.payload), ValidInterval(valid.end, old.valid.end), TransactionInterval(recorded_at)))
        additions.append(TemporalVersion(fact_id, dict(payload), valid, TransactionInterval(recorded_at)))
        self.rows = rows + additions
        return additions[-1]
# P10.07

# P10.08
