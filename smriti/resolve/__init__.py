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
        if name.startswith(("self.", "cls.")) and self.symbols[scope].kind == "method":
            return self.children.get(self.parents[scope], {}).get(name.split(".", 1)[1])
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
                else:
                    target = self.external_reference(call["name"], call["scope"])
                    edges.append(Edge(call["scope"], target, "calls", 0.5))
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


    def resolve_import(self, name: str, scope: str, visited=None) -> str | None:
        visited = set() if visited is None else visited
        if (scope, name) in visited:
            return None
        visited.add((scope, name))
        head, *tail = name.split(".")
        declaration = self.imports.get((scope, head))
        if not declaration:
            return None
        module = declaration["module"]
        if declaration["level"]:
            owner = self.symbols[scope]
            while owner.kind != "module":
                owner = self.symbols[owner.parent_id]
            package = owner.qualname if owner.path.endswith("/__init__.py") else owner.qualname.rpartition(".")[0]
            components = package.split(".") if package else []
            ascend = declaration["level"] - 1
            if ascend > len(components):
                return None
            prefix = components[:len(components) - ascend]
            module = ".".join([*prefix, module] if module else prefix)
        imported = declaration["name"]
        qualified = ".".join(part for part in [module, imported, *tail] if part)
        for symbol in self.symbols.values():
            if symbol.qualname == qualified:
                return symbol.id
        owner = next((symbol for symbol in self.symbols.values() if symbol.kind == "module" and symbol.qualname == module), None)
        if owner and imported:
            target = self.resolve_import(".".join([imported, *tail]), owner.id, visited)
            if target:
                return target
        return None


    def external_reference(self, name: str, scope: str) -> str:
        import builtins
        owner = scope
        shadowed = False
        while owner:
            shadowed = shadowed or (owner, name) in self.bindings
            owner = self.parents.get(owner)
        if "." not in name and hasattr(builtins, name) and not shadowed:
            return "builtin:" + name
        head, *tail = name.split(".")
        owner = scope
        while owner:
            declaration = self.imports.get((owner, head))
            if declaration:
                return "external:" + ".".join(part for part in [declaration["module"], declaration["name"], *tail] if part)
            owner = self.parents.get(owner)
        return "dynamic:" + scope + ":" + name


    def own_method(self, class_id: str, name: str) -> str | None:
        return self.children.get(class_id, {}).get(name)


def c3_linearize(class_id: str, bases: dict[str, list[str]], stack=()) -> list[str]:
    """Compute Python's C3 MRO and reject cyclic or inconsistent inheritance."""
    if class_id in stack:
        raise ValueError("Inheritance cycle")
    parents = bases.get(class_id, [])
    sequences = [c3_linearize(parent, bases, (*stack, class_id)) for parent in parents] + [list(parents)]
    result = [class_id]
    while any(sequences):
        sequences = [sequence for sequence in sequences if sequence]
        candidate = next((sequence[0] for sequence in sequences
            if all(sequence[0] not in other[1:] for other in sequences)), None)
        if candidate is None:
            raise ValueError("Inconsistent C3 inheritance order")
        result.append(candidate)
        for sequence in sequences:
            if sequence and sequence[0] == candidate:
                sequence.pop(0)
    return result
