# Scope-aware resolution

Python scopes link modules, classes, functions and nested definitions. Lookup considers local definitions and assignment aliases, enclosing lexical scopes, module globals, aliased and relative imports, and supported re-exports. Parameters and unknown assignment values shadow outer bindings. Comprehension targets remain isolated from enclosing bindings.

`self`, `cls`, and zero-argument `super()` method calls use Python C3 ordering. Cyclic and inconsistent hierarchies remain unresolved. Exact lexical calls have confidence 1; method dispatch has confidence 0.9; external references have confidence 0.5; same-name dynamic candidates are separate `may_call` edges with confidence 0.25.

The graph stores defines, contains, calls, imports, inherits and test edges. Test associations require a resolved call from a test-named function in a test-named file. `Resolver.callers` and `callees` return internal symbols and omit uncertain candidates by default. Graph persistence uses versioned JSON and atomic replacement.

## Validation

`tests/test_resolve.py` contains hand-labelled lexical and inheritance fixtures, negative cases, C3 oracle cases, persistence round trips, and agreement checks against Jedi for direct, nested and inherited calls. `docs/resolution-metrics.json` reports precision and recall on the small labelled fixture only; these numbers do not describe arbitrary repositories.

## Limits

Runtime monkey-patching, decorators that replace functions, metaclasses, reflection, dependency injection, overloaded operators, star imports, and arbitrary computed imports are not statically exact. A method body resolves `self` against its declared class; runtime subclass instances can dispatch differently. Instance-variable type inference and path-sensitive control-flow analysis are outside the MVP. Dynamic calls retain external/dynamic reference identities and may-call candidates, never an assertion of exact resolution. Unresolved external bases can change MRO; results should be reviewed when dependencies are unavailable. Java and TypeScript currently provide structural extraction, not Python-equivalent resolution. Go and C/C++ are staged optional extensions.
