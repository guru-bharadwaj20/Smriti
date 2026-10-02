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
Installing both into one environment would make the two scripts collide;
so install them in separate environments.
