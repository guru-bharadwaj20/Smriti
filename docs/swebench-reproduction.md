# CPU retrieval evaluation

Install the evaluation and vector extras (`pip install -e ".[eval,vectors]"`).
Run `python -m bench.swebench.datasets` to download the immutable test parquet
artifacts pinned in `bench/datasets.json`. Downloads are ignored Git files;
the committed artifact manifest records the publisher and measured SHA256,
row counts and immutable source URLs.

The manifest has 300 Lite and 500 Verified rows. There are 707 exact unique
evaluations: a shared instance reuses work only if repository, base commit,
issue text and gold patch all agree. Dataset-level reporting still counts
800 rows. Validation membership is a stable hash of instance ID across both
datasets. Tune on validation only; publish held-out scores separately.

Download the pinned model as documented in `docs/embeddings.md`, for example
`python -c "from smriti.vector.download import download_model; download_model('.smriti/models')"`.
Start an actual smoke with
`python -m bench.swebench.runner --limit 1 --repo psf/requests`, then continue
with `python -m bench.swebench.runner` for all tasks. This is a real CPU workload
and may take substantial time on the recorded four-thread i3 machine.

The runner validates every immutable artifact again, checks repository origin,
exact base SHA and clean worktree before indexing, and passes only the issue
text to retrieval. Gold patches remain outside indexed source and never enter
the model query. No task fix is applied. Checkout and index state live in the
ignored `.smriti/evaluation` workspace; embeddings are cached by content and
model version across commits. Production ANN state is isolated by repository.

Each completed unique task produces a flushed JSONL measurement. Restarting
reuses only records matching the exact configuration and source fingerprint.
The four baselines are substring grep, BM25F, exhaustive embedding cosine and
an explicitly Aider-style graph repo map. The latter is not the official Aider
implementation. Production retrieval uses the custom HNSW, fused search and
graph propagation. Ablations remove vectors, remove graph propagation or
replace the knapsack selection with greedy selection while retaining the
production representation, dependency and actual tokenizer checks.

File/function recall is measured at k=1,5,10,20,50. Production and ablation
context coverage is measured at 4096,8192,16384 tokens, including explanation
lines. Full enclosing bodies credit their contained functions. The minimum
budget covering gold is the minimum among these tested budgets: packing
coverage need not be monotone, so no binary search or exact minimum claim is
made. Empty gold is undefined and tooling failures remain failure records.

Run `python -m bench.swebench.report` for measured scope, split-specific macro
recall, p50/p95 latency and seeded instance-paired bootstrap confidence intervals.
The report identifies how many of the target unique evaluations and dataset
rows have actually been measured. Do not describe a partial report as the full
SWE-bench evaluation or replace failed measurements with invented scores.
