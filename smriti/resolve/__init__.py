"""Conservative lexical Python resolution and an auditable source graph."""
from smriti.models import Edge, Symbol
from smriti.parse import ParseResult


class Resolver:
    def __init__(self, results: list[ParseResult]):
        self.results = results
        self.symbols = {s.id: s for result in results for s in result.symbols}
        self.parents = {s.id: s.parent_id for s in self.symbols.values()}
        self.children = {}
        for symbol in self.symbols.values():
            if symbol.parent_id:
                self.children.setdefault(symbol.parent_id, {})[symbol.name] = symbol.id
        self.edges = []

    def resolve_name(self, name: str, scope: str) -> str | None:
        return self.children.get(scope, {}).get(name)

    def resolve(self) -> list[Edge]:
        edges = []
        for result in self.results:
            for call in result.calls:
                target = self.resolve_name(call["name"], call["scope"])
                if target:
                    edges.append(Edge(call["scope"], target, "calls"))
        self.edges = sorted(set(edges), key=lambda e: (e.source, e.kind, e.target))
        return self.edges
