# Reproducing the benchmarks

Every published number comes from a script in `bench/` and a result file that
is committed next to it. Commands assume the repository root and an environment
created with:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev,vectors,eval,ui]"
```

On Linux use `.venv/bin/python`. Reference hardware for the committed results is
an Intel Core i3-5005U (4 logical CPUs), 8 GB RAM, Windows 11, Python 3.13.1.

| Benchmark | Command | Output | Runtime on reference laptop |
| --- | --- | --- | --- |
| Component micro-benchmarks | `python scripts/search_benchmarks.py` | `bench/{lexical,vector,packing}/results.json` | minutes |
| Fusion weight tuning | `python scripts/fusion_tuning.py` | `bench/fusion/validation.json` | seconds |
| HNSW vs exact oracle | `python -m bench.vector.hnsw_reference` | `bench/vector/hnsw_reference.json` | minutes |
| Rust distance kernel | `pip install ./native` then `python -m bench.vector.native_profile` | `bench/vector/native_profile.json` | ~1 min; needs Rust |
| SWE-bench retrieval | see below | `.smriti/evaluation/` → `bench/swebench/results/` | ~5 min per task |
| CodeMem replay | see below | `bench/codemem/results/` | ~40 min |
| Rename survival | `python -m bench.codemem.renames --repo <clone>` | `bench/codemem/results/rename_survival.json` | ~15 min |
| Memory compression | `python -m bench.codemem.compression --database <replay db>` | `bench/codemem/results/compression.json` | seconds |
| LongMemEval retrieval | see below | `bench/longmemeval/results/` | ~30 min |

## SWE-bench (retrieval only)

Full details: [swebench-reproduction.md](swebench-reproduction.md).

```powershell
python -m bench.swebench.datasets                     # pinned Lite + Verified parquet
python -c "from smriti.vector.download import download_model; download_model('.smriti/models')"
python -m bench.swebench.runner --repo psf/requests   # repeat per repository, or omit --repo for all 707
python -m bench.swebench.report                       # summary, p50/p95, bootstrap CIs
```

Before retrieval, every task checks the base commit, origin and a clean checkout,
and `bench/swebench/leakage.py` confirms that the query contains no patch and
the index contains no post-fix lines. The committed results cover
`psf/requests`, `pallets/flask` and `mwaskom/seaborn` only.

## CodeMem commit replay

Full details: [bench/codemem/README.md](../bench/codemem/README.md).

```powershell
git clone --depth 260 --single-branch https://github.com/psf/requests.git .smriti/replay/requests
python -m bench.codemem.replay --repo .smriti/replay/requests --manifest bench/codemem/requests-200.json --output bench/codemem/results --probes 64
python -m bench.codemem.renames --repo .smriti/replay/requests
python -m bench.codemem.compression --database .smriti/replay/requests/.smriti/codemem.sqlite
```

The replay refuses a clone that has modified files or an existing replay
database. `injection.json` is deterministic: a fresh clone reproduces it byte for
byte.

## LongMemEval

Full details: [longmemeval.md](longmemeval.md).

```powershell
# Download longmemeval_s_cleaned.json from huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
# at revision 98d7416c24c778c2fee6e6f3006e7a073259d48f into .smriti/longmemeval/
python -m bench.longmemeval.runner .smriti/longmemeval/longmemeval_s_cleaned.json --output bench/longmemeval/results/longmemeval_s.jsonl
```

The runner verifies the file's SHA-256 and size against `manifest.json` and
resumes from an existing JSONL. Optional answer scoring of externally produced
hypotheses: `python -m bench.longmemeval.answers <dataset> <hypotheses.jsonl> --output <file>`.

## Determinism

Seeds are fixed (HNSW seed 17 for the native profile, 0 for SWE-bench ANN,
SHA-256 ranking for CodeMem probes and the validation split). Timings vary
between runs and machines. Labels, recall and precision are deterministic for a
given source revision and dataset.

## Expected results

A reproduction matches when deterministic values are equal and timings are of
the same order on comparable hardware.

| Output | Deterministic values to compare |
| --- | --- |
| `bench/codemem/results/metrics.json` | 12,736 observations; TP 87, FP 0, FN 0; exact cascade closure; 201 branches checked |
| `bench/codemem/results/injection.json` | byte-identical (64 probes) |
| `bench/codemem/results/rename_survival.json` | file moves 64/64 survived; identifier renames 64/64 flagged |
| `bench/codemem/results/compression.json` | `byte_identical`, `provenance_equal`, `signature_preserved` all true |
| `bench/longmemeval/results/longmemeval_s.summary.json` | 500 questions; session recall@5 0.8479 |
| `bench/swebench/results/report.json` | 16 measured tasks; held-out function recall@10 full 0.267, BM25 0.333 |
| `bench/vector/native_profile.json` | identical seeded graph and query IDs (speedup varies by machine) |
| `bench/agent/results.json` | depends on the model; the oracle check in `tests/test_agent_compare.py` must give 8/8 |
