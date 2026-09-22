
"""Content-addressed operations reference purgeable payload blobs."""
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
# P10.09
def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Operation:
    kind: str
    fact_id: str | None
    payload_hash: str | None
    parents: tuple[str, ...]
    recorded_at: str
    metadata: dict

    @property
    def id(self):
        return digest(asdict(self))

    def to_dict(self):
        return {"id": self.id, **asdict(self)}
# P10.10
