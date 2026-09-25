# Local state and ignored paths

The default state directory is `.smriti/` inside the repository and is ignored by
Git and indexing. It contains SQLite databases, Merkle snapshots, vector state,
and repository identity. Configure `data_dir` in `smriti.toml` or `SMRITI_DATA_DIR`.
Runtime configuration must also exclude a custom state directory from indexing.

Never index `.git`, virtual environments, caches, build outputs, symlink targets,
model weights, or ignored repository files. The scanner follows `.gitignore`
semantics, including nested rules, and always keeps internal state excluded.
Benchmark datasets and checkouts are ignored under `bench/data` and
`bench/checkouts`; ground-truth patches never enter retrieval input.
