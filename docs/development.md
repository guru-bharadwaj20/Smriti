# Development

Use Python 3.12 or newer. On Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev,vectors,ui]"
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m ruff check smriti tests bench
.venv/Scripts/python.exe -m ruff format --check smriti tests bench
.venv/Scripts/python.exe -m mypy smriti
```

On Linux replace `.venv/Scripts/python.exe` with `.venv/bin/python`.
Full vector inference requires a separately downloaded, pinned model artifact;
installation must not silently download large weights.

Choose one CONTRIBUTING task, implement and verify it, then use
`python scripts/task_commit.py ID "message" --evidence "files; checks" --files FILE...`.
The coordinator stages only those paths, updates the task, commits with the project
identity, and immediately pushes to the configured remote. A failed push stops
the worker. Never edit another worker's files while its commit is pending.
