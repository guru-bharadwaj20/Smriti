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
        self.imports = {(item["scope"], item["alias"]): item for result in self.results for item in result.imports}
        self.bindings = {}
        self.declarations = {}
        self._bind()

    def resolve_name(self, name: str, scope: str, visited=None) -> str | None:
        visited = set() if visited is None else visited
        if (scope, name) in visited:
            return None
        visited.add((scope, name))
        declaration = self.declarations.get((scope, name))
        if declaration:
            parent = self.parents.get(scope)
            if declaration == "global":
                while parent and self.parents.get(parent):
                    parent = self.parents[parent]
            elif parent and self.symbols[parent].kind == "class":
                parent = self.parents.get(parent)
            return self.resolve_name(name, parent, visited) if parent else None
        binding = self.bindings.get((scope, name), "@missing")
        if binding is None:
            return None
        if binding != "@missing" and binding != name:
            return self.resolve_name(binding, scope, visited)
        target = self.resolve_import(name, scope) or self.children.get(scope, {}).get(name)
        if target:
            return target
        parent = self.parents.get(scope)
        while parent and self.symbols[parent].kind == "class":
            parent = self.parents.get(parent)
        if parent:
            return self.resolve_name(name, parent, visited)
        qualified = {s.qualname: s.id for s in self.symbols.values()}
        return qualified.get(name)

    def resolve(self) -> list[Edge]:
        edges = []
        for result in self.results:
            for call in result.calls:
                target = self.resolve_name(call["name"], call["scope"])
                if target:
                    edges.append(Edge(call["scope"], target, "calls"))
        self.edges = sorted(set(edges), key=lambda e: (e.source, e.kind, e.target))
        return self.edges


    def _bind(self):
        import ast
        for result in self.results:
            try:
                tree = ast.parse(result.source)
            except SyntaxError:
                continue
            by_location = {(s.start_line, s.name): s.id for s in result.symbols if s.kind != "module"}
            def visit(node, scope):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    scope = by_location.get((node.lineno, node.name), scope)
                    if hasattr(node, "args"):
                        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                        arguments += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
                        for argument in arguments:
                            self.bindings[(scope, argument.arg)] = None
                if isinstance(node, ast.Global):
                    for name in node.names:
                        self.declarations[(scope, name)] = "global"
                if isinstance(node, ast.Nonlocal):
                    for name in node.names:
                        self.declarations[(scope, name)] = "nonlocal"
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            self.bindings[(scope, target.id)] = node.value.id if isinstance(node.value, ast.Name) else None
                for child in ast.iter_child_nodes(node):
                    visit(child, scope)
            visit(tree, result.symbols[0].id)


    def resolve_import(self, name: str, scope: str) -> str | None:
        head, *tail = name.split(".")
        declaration = self.imports.get((scope, head))
        if not declaration:
            return None
        module = declaration["module"]
        imported = declaration["name"]
        qualified = ".".join(part for part in [module, imported, *tail] if part)
        for symbol in self.symbols.values():
            if symbol.qualname == qualified:
                return symbol.id
        return None
