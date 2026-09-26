"""Reproduce the recorded deterministic component benchmark."""
import runpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
namespace=runpy.run_path(str(Path(__file__).resolve().parents[2]/"scripts/search_benchmarks.py"))
import json
print(json.dumps(namespace["lexical"](),indent=2))
