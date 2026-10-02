# Native parser compatibility

Smriti bounds the Python `tree-sitter` dependency to `>=0.25.2,<0.26`.
Version 0.26.0 crashed while repeatedly indexing real Requests modules in this
Windows/Python 3.13.1 workspace, both with incremental trees and cold parse caches.
A separate 35-file parse-and-resolution loop also crashed after three sweeps.

The upstream report [issue 472](https://github.com/tree-sitter/py-tree-sitter/issues/472)
describes a matching native use-after-free regression in 0.26.0 and identifies
0.25.2 as a workaround. [Issue 500](https://github.com/tree-sitter/py-tree-sitter/issues/500)
tracks publication of the upstream fix. The bounded release keeps incremental
tree reuse enabled; Smriti does not silently disable indexing or fabricate results.

Before widening this bound, run repeated real-module extraction, incremental
fresh-tree equivalence tests, and the commit-history replay in a single process.

After downgrading to 0.25.2, the same Requests workload completed 30 sweeps of
35 real modules (1,050 parses), alternating a trailing source edit and resolving
the graph after each sweep, without a native exception. A permanent regression
test exercises repeated incremental extraction of stdlib argparse and inspect.
