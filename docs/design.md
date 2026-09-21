# Design decisions

## P01.01: Language scope

The initial supported language is Python 3.12+. Python symbol extraction uses
tree-sitter and name resolution is deliberately static: dynamic dispatch produces
uncertain candidate edges rather than a claim of runtime certainty. TypeScript
and Java extraction follow with language-specific fixtures. Go and C/C++ are
optional extensions; their absence must remain visible in the checklist.

Core operation is local and CPU-only. Embeddings and local model summaries are
optional capabilities with explicit model configuration; no paid API is required.
