"""Half-open valid and transaction intervals for historical memory."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any


def timestamp(value: datetime | str) -> datetime:
    point = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(point, datetime) or point.tzinfo is None or point.utcoffset() is None:
        raise ValueError('Timestamp must be timezone-aware')
    return point.astimezone(UTC)


@dataclass(frozen=True, init=False)
class ValidInterval:
    start: datetime
    end: datetime | None = None

    def __init__(self, start: datetime | str, end: datetime | str | None = None) -> None:
        first = timestamp(start)
        last = timestamp(end) if end is not None else None
        if last is not None and last <= first:
            raise ValueError('Interval end must be after start')
        object.__setattr__(self, 'start', first)
        object.__setattr__(self, 'end', last)

    def contains(self, point: datetime | str) -> bool:
        return self.start <= timestamp(point) and (self.end is None or timestamp(point) < self.end)


@dataclass(frozen=True, init=False)
class TransactionInterval(ValidInterval):
    """The period during which Smriti believed a version."""


@dataclass(frozen=True)
class TemporalVersion:
    fact_id: str
    payload: dict[str, Any]
    valid: ValidInterval
    transaction: TransactionInterval


class Timeline:
    """In-memory bitemporal oracle, also used by persistent log replay."""

    def __init__(self, versions: list[TemporalVersion] | tuple[TemporalVersion, ...] = ()) -> None:
        self.rows = list(versions)

    def valid_at(self, point: datetime | str) -> list[TemporalVersion]:
        point = timestamp(point)
        return [v for v in self.rows if v.valid.contains(point)]

    def query(self, valid_at: datetime | str, as_of: datetime | str) -> list[TemporalVersion]:
        as_of = timestamp(as_of)
        return [v for v in self.valid_at(valid_at) if v.transaction.contains(as_of)]

    def correct(
        self,
        fact_id: str,
        payload: dict[str, Any],
        valid: ValidInterval,
        recorded_at: datetime | str,
    ) -> TemporalVersion:
        """Correct the overlap, retaining both old beliefs and unaffected times."""
        recorded_at = timestamp(recorded_at)
        additions = []
        rows = []
        for old in self.rows:
            overlap = (old.valid.end is None or valid.start < old.valid.end) and (
                valid.end is None or old.valid.start < valid.end
            )
            if old.fact_id != fact_id or old.transaction.end is not None or (not overlap):
                rows.append(old)
                continue
            if recorded_at <= old.transaction.start:
                raise ValueError('Corrections must advance transaction time')
            rows.append(
                replace(old, transaction=TransactionInterval(old.transaction.start, recorded_at))
            )
            if old.valid.start < valid.start:
                additions.append(
                    TemporalVersion(
                        fact_id,
                        dict(old.payload),
                        ValidInterval(old.valid.start, valid.start),
                        TransactionInterval(recorded_at),
                    )
                )
            if valid.end is not None and (old.valid.end is None or valid.end < old.valid.end):
                additions.append(
                    TemporalVersion(
                        fact_id,
                        dict(old.payload),
                        ValidInterval(valid.end, old.valid.end),
                        TransactionInterval(recorded_at),
                    )
                )
        additions.append(
            TemporalVersion(fact_id, dict(payload), valid, TransactionInterval(recorded_at))
        )
        self.rows = rows + additions
        return additions[-1]
