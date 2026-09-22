
"""Content-addressed operations reference purgeable payload blobs."""
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
# P10.09
