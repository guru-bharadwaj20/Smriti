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

## Clean-install smoke test

Install the wheel into a fresh environment and run the smoke script from outside
the source tree, so the installed package rather than the checkout is imported:

```powershell
python -m venv $env:TEMP/smriti-clean
$env:TEMP/smriti-clean/Scripts/python.exe -m pip install dist/smriti_engine-0.1.0-py3-none-any.whl
cd $env:TEMP
$env:TEMP/smriti-clean/Scripts/python.exe <repo>/scripts/smoke_install.py
```

It indexes a temporary repository with the `smriti` console script, checks
`find-symbol`, `callers`, `context`, `remember` and `recall`, then starts
`smriti serve` over MCP stdio, lists the tools and calls `find_symbol` and
`context`. Verified 2 October 2026 on Windows 11 / Python 3.13.1 with only the
wheel's declared dependencies installed; all 14 MCP tools were listed.
