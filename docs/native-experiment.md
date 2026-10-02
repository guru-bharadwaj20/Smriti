# Optional Rust distance experiment

`bench/vector/native_profile.py` profiles the actual custom HNSW at 384 dimensions,
then conditionally compares a Rust/PyO3 distance kernel. The Rust source retains
left-to-right f64 accumulation and does not enable fast-math. Python-to-Rust
conversion costs are included in the timed end-to-end build and query run.
The comparison requires equal seeded graphs, exact query IDs and distance
agreement within 1e-12. The unprofiled Python timing is the speed baseline.

The optional crate pins PyO3 0.29.3, verified from the primary crates.io API.
See [PyO3 build documentation](https://pyo3.rs/main/building-and-distribution)
and [Maturin tutorial](https://www.maturin.rs/tutorial.html).
With a Rust toolchain and platform linker available, run
`python -m pip install ./native` from the repository root, then
`python -m bench.vector.native_profile`.

## Measured result (2 October 2026)

Toolchain: Rust 1.99.0 (`x86_64-pc-windows-gnu`), PyO3 0.29.3, built with
`pip install ./native`; `native/Cargo.lock` pins all 14 crates. Hardware: Intel
Core i3-5005U, 4 logical CPUs, 8 GB RAM, Windows 11, Python 3.13.1. Seed 17,
120 vectors, 384 dimensions, 20 queries (`bench/vector/native_profile.json`).

| Measurement | Value |
| --- | --- |
| Profiled Python build + query | 48.30 s |
| Time inside `vector.math.distance` (cumulative) | 46.39 s (96%) |
| Unprofiled Python build + query | 18.78 s |
| Rust/PyO3 distance, same workload | 2.81 s |
| End-to-end speedup | 6.69x |
| Seeded HNSW graph identical | yes |
| Query result IDs identical | yes |
| Max distance difference | below 1e-12 on all 120 pairs |

The profile identifies the pure-Python dot product as the only hot path worth
moving; graph maintenance and heap operations are under 4%. The native module is
optional: production code still imports the Python implementation, and the
comparison patches it in only inside the benchmark. Results are one run on one
machine, not a distribution.
