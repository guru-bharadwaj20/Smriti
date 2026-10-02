# Release checklist

## Package name (checked 2 October 2026)

| Name | PyPI JSON API | Simple index | Status |
| --- | --- | --- | --- |
| `smriti-engine` | 404 | 404 | Available; used in `pyproject.toml` |
| `smriti` | 200 | — | Taken: an unrelated screen-session manager (`project-vajra/smriti`, 0.0.1) |
| `smriti-mcp` | 200 | — | Taken |

PEP 503 normalization makes `smriti_engine` and `smriti.engine` the same project
as `smriti-engine`. Availability can change until the first upload; recheck
`https://pypi.org/pypi/smriti-engine/json` immediately before publishing.

The unrelated `smriti` distribution may also install a `smriti` console command.
Installing both into one environment would make the two scripts collide, so
install them in separate environments.

## Build and check the artifacts

```powershell
.venv/Scripts/python.exe -m build --outdir dist
.venv/Scripts/python.exe -m twine check dist/*
```

Verified 2 October 2026: `smriti_engine-0.1.0-py3-none-any.whl` and
`smriti_engine-0.1.0.tar.gz` build and pass `twine check`. The wheel holds 60
entries: the 54 `smriti/` package files (Python modules, `py.typed`, UI static
assets, `vector/model_manifest.json`) and dist-info with the MIT license. Tests,
benchmarks, scripts and model weights are not packaged. The console entry point
is `smriti = smriti.server.cli:app`.
