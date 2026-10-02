# Third-party license review

Smriti is MIT licensed. It vendors no third-party source: dependencies are
installed from PyPI and model weights and datasets are downloaded separately
after checksum verification. Versions below are the ones installed and tested
in the development environment on 2 October 2026, read from each package's
installed metadata.

## Runtime dependencies

| Package | Tested version | License |
| --- | --- | --- |
| typer | 0.27.2 | MIT |
| mcp | 2.2.0 | MIT |
| pydantic | 2.13.5 | MIT |
| tree-sitter | 0.25.2 | MIT |
| tree-sitter-python / -typescript / -java | 0.25.0 / 0.23.2 / 0.23.5 | MIT |
| tree-sitter-go / -c / -cpp | 0.25.0 / 0.24.2 / 0.23.4 | MIT |
| pathspec | 1.1.1 | MPL-2.0 |
| watchdog | 6.0.0 | Apache-2.0 |
| tiktoken | 0.14.0 | MIT |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |

## Optional extras

| Extra | Package | Tested version | License |
| --- | --- | --- | --- |
| `vectors` | onnxruntime | 1.30.0 | MIT |
| `vectors` | tokenizers | 0.23.2 | Apache-2.0 |
| `ui` | fastapi | 0.142.2 | MIT |
| `ui` | uvicorn | 0.54.0 | BSD-3-Clause |
| `ui` | starlette (via fastapi) | 1.7.0 | BSD-3-Clause |
| `eval` | pyarrow | ≥25,<26 | Apache-2.0 |

`dev` tools (pytest, hypothesis, ruff, mypy, build, jedi, scipy) are not
distributed with Smriti.

## Model and data

| Artifact | Source | License | Notes |
| --- | --- | --- | --- |
| all-MiniLM-L6-v2 ONNX + tokenizer | `sentence-transformers/all-MiniLM-L6-v2` @ `1110a243` | Apache-2.0 | Optional; pinned SHA-256 in `smriti/vector/model_manifest.json`; never downloaded implicitly |
| LongMemEval-S cleaned | `xiaowu0162/longmemeval-cleaned` @ `98d7416c` | MIT | Benchmark only; not redistributed |
| SWE-bench Lite / Verified | `princeton-nlp` datasets, pinned revisions | No license declared on the dataset card | Benchmark only; not redistributed; task repositories keep their own licenses |
| Requests commit history | `psf/requests` | Apache-2.0 | CodeMem replay; only commit IDs, symbol hashes and labels are published |

## Findings

- All runtime and optional dependencies use permissive licenses compatible with
  distributing Smriti under MIT.
- pathspec is MPL-2.0, a file-level weak copyleft license. Using it as an
  unmodified installed dependency places no obligation on Smriti's own source.
  Modified copies of pathspec files would have to stay under MPL-2.0.
- Apache-2.0 components (watchdog, tokenizers, the embedding model) require
  their NOTICE and license to accompany any redistribution of those components
  themselves. Smriti's wheel does not bundle them.
- SWE-bench declares no dataset license, so Smriti publishes only derived metrics
  and instance IDs, never task text or patches.
