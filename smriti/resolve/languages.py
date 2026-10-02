"""Conservative direct-call resolution for Go and C-family sources."""

from smriti.models import Edge, Symbol
from smriti.parse import ParseResult


def resolve_calls(results: list[ParseResult]) -> list[Edge]:
    symbols = {symbol.id: symbol for result in results for symbol in result.symbols}
    owners = {symbol.id: result for result in results for symbol in result.symbols}
    receivers = {
        identity: binding
        for result in results
        for identity, binding in result.receiver_bindings.items()
    }
    children: dict[str, list[Symbol]] = {}
    for symbol in symbols.values():
        if symbol.parent_id:
            children.setdefault(symbol.parent_id, []).append(symbol)
    edges = []
    for result in results:
        if result.language not in {'go', 'c', 'cpp'}:
            continue
        for call in result.calls:
            name = call['name'].replace('::', '.')
            scope = symbols[call['scope']]
            candidates: list[Symbol] = []
            if name in result.local_names.get(scope.id, set()):
                pass
            elif result.language == 'go' and '.' in name and scope.id in receivers:
                variable, typename = receivers[scope.id]
                prefix, method = name.split('.', 1)
                if prefix == variable:
                    candidates = [
                        symbol
                        for symbol in symbols.values()
                        if symbol.name == method
                        and receivers.get(symbol.id, ('', ''))[1] == typename
                        and owners[symbol.id].package == result.package
                    ]
            elif name.startswith('this->'):
                owner = symbols.get(scope.parent_id or '')
                if owner:
                    candidates = [
                        symbol for symbol in children.get(owner.id, []) if symbol.name == name[6:]
                    ]
            elif '.' in name:
                candidates = [
                    symbol
                    for symbol in symbols.values()
                    if (symbol.qualname.endswith('.' + name) or symbol.qualname == name)
                    and owners[symbol.id].language == result.language
                ]
            else:
                current: Symbol | None = scope
                while current and not candidates:
                    candidates = [
                        symbol
                        for symbol in children.get(current.id, [])
                        if symbol.name == name and symbol.kind in {'function', 'method'}
                    ]
                    current = symbols.get(current.parent_id or '')
                if not candidates and result.language == 'go':
                    candidates = [
                        symbol
                        for symbol in symbols.values()
                        if symbol.name == name
                        and symbol.kind == 'function'
                        and owners[symbol.id].language == 'go'
                        and owners[symbol.id].package == result.package
                    ]
                if not candidates and result.language in {'c', 'cpp'}:
                    includes = {item['module'] for item in result.imports}
                    candidates = [
                        symbol
                        for symbol in symbols.values()
                        if symbol.name == name
                        and symbol.kind == 'function'
                        and symbol.path in includes
                    ]
            if len(candidates) == 1:
                edges.append(Edge(scope.id, candidates[0].id, 'calls', 0.9))
            else:
                edges.append(Edge(scope.id, f'external:{result.language}:{name}', 'calls', 0.4))
                edges.extend(
                    Edge(scope.id, candidate.id, 'may_call', 0.25) for candidate in candidates
                )
    return edges
