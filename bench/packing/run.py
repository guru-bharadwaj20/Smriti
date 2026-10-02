"""Reproduce the recorded deterministic component benchmark."""

import json
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
namespace = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / 'scripts/search_benchmarks.py')
)

print(json.dumps(namespace['packing'](), indent=2))
