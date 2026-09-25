# Retrieval ground-truth policy

SWE-bench retrieval indexes only the task's clean base commit and queries only
the issue text. Fix and test patches are evaluation inputs stored outside that
checkout; they must never be applied before retrieval or included in embeddings.

File recall includes changed file paths, including new paths that cannot be found
at the base commit. Report those impossible-at-base cases separately. Function
recall uses existing base-commit functions and methods intersecting changed lines,
not surrounding hunk context. Nested changes credit the innermost function.

Deleted functions can be retrieved from the base commit and remain in the gold
set. Completely new functions have no base symbol; exclude them from the
base-function denominator and report their count explicitly. Added lines within
an existing function map to their insertion location in base source. Changes to
module-only code or unsupported languages remain visible in file metrics even
when function-level ground truth is empty.

Empty function ground truth produces `null` for function recall, not 100%.
Aggregate averages report both eligible and excluded task counts. Budget recall
must specify whether any representation counts or whether the full function body
is required. Do not turn retrieval-only memory metrics into answer-accuracy claims.
