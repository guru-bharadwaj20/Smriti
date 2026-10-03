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
