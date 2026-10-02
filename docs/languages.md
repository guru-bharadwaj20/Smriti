# Go, C and C++

`SourceParser.parse(path, source, language)` accepts `go`, `c` and `cpp` in
addition to Python, TypeScript and Java. All use real tree-sitter grammars and
retain exact source bytes and incremental trees.

| Language | Extracted structure | Resolution policy |
| --- | --- | --- |
| Go | Packages, imports, named types, functions, receiver methods, calls | Lexical calls and same-package functions; receiver methods matched by declared receiver type |
| C | Function bodies, includes, calls | Unique lexical direct calls; unresolved function pointers remain external |
| C++ | Namespaces, classes, functions, methods, includes, calls | Unique lexical or qualified direct calls; overloaded targets become `may_call` candidates |

C++ namespaces are represented as class-like graph containers because the shared
symbol contract has no namespace kind. This engine does not run a compiler,
expand macros, instantiate templates or prove overload selection. Go interfaces,
reflection and arbitrary variable type inference also require compiler information;
unknown calls remain uncertain. Include paths are retained as written, without a
compiler include-search path.

`smriti.resolve.api.ApiBinding` describes an explicit consumer or provider using
a stable symbol ID, protocol and endpoint. `cross_language_edges(symbols, bindings)`
links matching endpoints across languages, including HTTP and gRPC declarations.
Protocols should include method names where relevant, such as `http:POST`.
Missing anchors fail clearly. Multiple providers produce uncertain edges. These
declared boundary edges carry confidence 0.8 and are not compiler-proven calls.
No cross-language call is inferred solely from similar function names.
