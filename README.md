# Smriti

A local memory and context engine for coding agents. It runs on CPU and connects
through the Model Context Protocol (MCP).

Smriti finds the code relevant to a task and packs it into a fixed token budget.
It also keeps facts across sessions. Facts are anchored to the exact code they
describe, so editing that code marks them stale. Memory has git-like history:
branches that follow your Git branches, three-way merges, rollback, and
irreversible cascading deletion.

## Install

Requires Python 3.12 or newer.

```sh
git clone https://github.com/guru-bharadwaj20/SMRITI.git
cd SMRITI
python -m venv .venv
.venv/Scripts/python.exe -m pip install .        # Linux/macOS: .venv/bin/python
```

Optional extras: `.[vectors]` for semantic search (ONNX embeddings), `.[ui]` for
the local web UI, `.[dev]` for tests and linters. A container build is described
in [docs/docker.md](docs/docker.md).

## Use

Run these inside the repository you want to index (or pass `--root PATH`):

```sh
smriti index                                         # incremental; reruns only changed files
smriti status
smriti find-symbol parse_header
smriti callers parse_header
smriti context "fix header parsing for empty values" --budget 8000
smriti remember "parse_header must keep the original casing" --anchor SYMBOL_ID=CONTENT_HASH
smriti recall "header casing"
smriti memory log
smriti forget FACT_ID                                # also deletes facts derived from it
```

`find-symbol` prints each symbol's `id` and `content_hash` for use in `--anchor`.
After an edit, `smriti index` marks anchored facts `stale` or `orphaned`, and
`recall --fresh-only` hides them.

## Connect a coding agent

```sh
smriti serve --root /path/to/repo                    # MCP over stdio
```

The server exposes 14 tools: `context`, `find_symbol`, `callers`, `callees`,
`status`, `remember`, `recall`, `forget` and `memory_log`, `memory_diff`,
`memory_revert`, `memory_branch`, `memory_switch`, `memory_merge`. Client
configuration examples are in [docs/mcp-setup.md](docs/mcp-setup.md).

## Results

Measured on an Intel i3-5005U laptop (details in [docs/benchmarks.md](docs/benchmarks.md)):

| Benchmark | Result |
| --- | --- |
| CodeMem: 200 real `psf/requests` commits, 64 anchored facts | stale detection precision 1.0, recall 1.0 (12,736 labels) |
| Anchors through file moves / identifier renames | 64/64 kept fresh / 64/64 flagged |
| Cascading forget on a derivation diamond | exact closure, 0 facts resurrected across 201 branches |
| LongMemEval-S (500 questions, retrieval only) | session recall@5 0.848 |
| Memory archive compression (real replay log) | 0.21 of original size, byte-identical |
| Optional Rust distance kernel | 6.7x faster HNSW build+query, identical results |

SWE-bench retrieval results for a three-repository subset are in
[docs/report.md](docs/report.md). Limits are listed in
[docs/limitations.md](docs/limitations.md).

## Documentation

- [Architecture and storage formats](docs/architecture.md)
- [Memory semantics: time, deletion, freshness](docs/memory-semantics.md)
- [Languages](docs/languages.md) · [Resolution](docs/resolution.md) · [Packing](docs/packing.md)
- [Benchmarks](docs/benchmarks.md) · [Prior work](docs/prior-work.md) · [Licenses](docs/licenses.md)
- [Development setup](docs/development.md) · [Contributing checklist](CONTRIBUTING.md)

**License:** [MIT](LICENSE).
