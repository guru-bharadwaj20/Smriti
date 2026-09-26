"""Global dataset-independent instance splits avoid Lite/Verified overlap leakage."""

import hashlib
from collections.abc import Iterable

SPLIT_POLICY = 'sha256(instance_id) first 8 digest bytes modulo 5 equals zero -> validation; otherwise held_out'


def instance_split(instance_id: str) -> str:
    if not instance_id:
        raise ValueError('instance ID is required')
    value = int.from_bytes(hashlib.sha256(instance_id.encode()).digest()[:8], 'big')
    return 'validation' if value % 5 == 0 else 'held_out'


def split_instances(instance_ids: Iterable[str]) -> dict[str, list[str]]:
    result = {'validation': [], 'held_out': []}
    for id in sorted(set(instance_ids)):
        result[instance_split(id)].append(id)
    return result
