"""Conservative lexical Python resolution and an auditable source graph."""

from pathlib import Path

from smriti.models import Edge, Symbol
from smriti.parse import ParseResult


class Resolver:
    def __init__(self, results: list[ParseResult]):
        self.results = results
        self.symbols = {s.id: s for result in results for s in result.symbols}
        self.parents = {s.id: s.parent_id for s in self.symbols.values()}
        self.children: dict[str, dict[str, str]] = {}
        for symbol in self.symbols.values():
            if symbol.parent_id:
                self.children.setdefault(symbol.parent_id, {})[symbol.name] = symbol.id
        self.edges: list[Edge] = []
        self.imports = {
            (item['scope'], item['alias']): item
            for result in self.results
            for item in result.imports
        }
        self.bindings: dict[tuple[str, str], str | None] = {}
        self.declarations: dict[tuple[str, str], str] = {}
        self._bind()

    def resolve_name(
        self, name: str, scope: str, visited: set[tuple[str, str]] | None = None
    ) -> str | None:
        visited = set() if visited is None else visited
        if (scope, name) in visited:
            return None
        visited.add((scope, name))
        declaration = self.declarations.get((scope, name))
        if declaration:
            parent = self.parents.get(scope)
            if declaration == 'global':
                while parent and self.parents.get(parent):
                    parent = self.parents[parent]
            elif parent and self.symbols[parent].kind == 'class':
                parent = self.parents.get(parent)
            return self.resolve_name(name, parent, visited) if parent else None
        if name.startswith('super().') and self.symbols[scope].kind == 'method':
            return self.method_target(
                self.symbols[scope].parent_id or '', name[len('super().') :], skip_current=True
            )
        if name.startswith(('self.', 'cls.')) and self.symbols[scope].kind == 'method':
            return self.method_target(self.symbols[scope].parent_id or '', name.split('.', 1)[1])
        binding = self.bindings.get((scope, name), '@missing')
        if binding is None:
            return None
        if binding != '@missing' and binding != name:
            return self.resolve_name(binding, scope, visited)
        target = self.resolve_import(name, scope) or self.children.get(scope, {}).get(name)
        if target:
            return target
        parent = self.parents.get(scope)
        while parent and self.symbols[parent].kind == 'class':
            parent = self.parents.get(parent)
        if parent:
            return self.resolve_name(name, parent, visited)
        qualified = {s.qualname: s.id for s in self.symbols.values()}
        return qualified.get(name)

    def resolve(self) -> list[Edge]:
        edges = []
        for result in self.results:
            for call in result.calls:
                target = self.resolve_name(call['name'], call['scope'])
                if target:
                    edges.append(
                        Edge(
                            call['scope'],
                            target,
                            'calls',
                            self.edge_confidence(call['name'], target),
                        )
                    )
                else:
                    target = self.external_reference(call['name'], call['scope'])
                    edges.append(Edge(call['scope'], target, 'calls', 0.5))
                    for candidate in self.dynamic_candidates(call['name']):
                        edges.append(Edge(call['scope'], candidate, 'may_call', 0.25))
        edges.extend(self.structural_edges())
        edges.extend(self.import_edges())
        edges.extend(self.inheritance_edges())
        edges.extend(self.test_associations(edges))
        self.edges = sorted(set(edges), key=lambda e: (e.source, e.kind, e.target))
        return self.edges

    def _bind(self) -> None:
        import ast

        for result in self.results:
            try:
                tree = ast.parse(result.source)
            except SyntaxError:
                continue
            by_location = {}
            for symbol in result.symbols:
                if symbol.kind == 'module':
                    continue
                # Symbol ranges include decorators; ast.lineno points at the definition.
                offset = next(
                    (
                        index
                        for index, line in enumerate(symbol.signature.splitlines())
                        if line.lstrip().startswith(('def ', 'async def ', 'class '))
                    ),
                    0,
                )
                by_location[(symbol.start_line + offset, symbol.name)] = symbol.id

            def visit(
                node: ast.AST,
                scope: str,
                locations: dict[tuple[int, str], str] = by_location,
            ) -> None:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    scope = locations.get((node.lineno, node.name), scope)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                        arguments += [arg for arg in (node.args.vararg, node.args.kwarg) if arg]
                        for argument in arguments:
                            self.bindings[(scope, argument.arg)] = None
                if isinstance(node, ast.Global):
                    for name in node.names:
                        self.declarations[(scope, name)] = 'global'
                if isinstance(node, ast.Nonlocal):
                    for name in node.names:
                        self.declarations[(scope, name)] = 'nonlocal'
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            self.bindings[(scope, target.id)] = (
                                node.value.id if isinstance(node.value, ast.Name) else None
                            )
                for child in ast.iter_child_nodes(node):
                    visit(child, scope)

            visit(tree, result.symbols[0].id)

    def resolve_import(
        self, name: str, scope: str, visited: set[tuple[str, str]] | None = None
    ) -> str | None:
        visited = set() if visited is None else visited
        if (scope, name) in visited:
            return None
        visited.add((scope, name))
        head, *tail = name.split('.')
        declaration = self.imports.get((scope, head))
        if not declaration:
            return None
        module = declaration['module']
        if declaration['level']:
            owner = self.symbols[scope]
            while owner.kind != 'module':
                assert owner.parent_id is not None
                owner = self.symbols[owner.parent_id]
            package = (
                owner.qualname
                if owner.path.endswith('/__init__.py')
                else owner.qualname.rpartition('.')[0]
            )
            components = package.split('.') if package else []
            ascend = declaration['level'] - 1
            if ascend > len(components):
                return None
            prefix = components[: len(components) - ascend]
            module = '.'.join([*prefix, module] if module else prefix)
        imported = declaration['name']
        qualified = '.'.join(part for part in [module, imported, *tail] if part)
        for symbol in self.symbols.values():
            if symbol.qualname == qualified:
                return symbol.id
        module_owner = next(
            (
                symbol
                for symbol in self.symbols.values()
                if symbol.kind == 'module' and symbol.qualname == module
            ),
            None,
        )
        if module_owner and imported:
            target = self.resolve_import('.'.join([imported, *tail]), module_owner.id, visited)
            if target:
                return target
        return None

    def external_reference(self, name: str, scope: str) -> str:
        import builtins

        owner: str | None = scope
        shadowed = False
        while owner:
            shadowed = shadowed or (owner, name) in self.bindings
            owner = self.parents.get(owner)
        if '.' not in name and hasattr(builtins, name) and not shadowed:
            return 'builtin:' + name
        head, *tail = name.split('.')
        owner = scope
        while owner:
            declaration = self.imports.get((owner, head))
            if declaration:
                return 'external:' + '.'.join(
                    part for part in [declaration['module'], declaration['name'], *tail] if part
                )
            owner = self.parents.get(owner)
        return 'dynamic:' + scope + ':' + name

    def own_method(self, class_id: str, name: str) -> str | None:
        return self.children.get(class_id, {}).get(name)

    def class_bases(self) -> dict[str, list[str]]:
        bases: dict[str, list[str]] = {}
        for result in self.results:
            for declaration in result.inheritance:
                target = self.resolve_name(declaration['name'], declaration['scope'])
                if target and self.symbols[target].kind == 'class':
                    bases.setdefault(declaration['class'], []).append(target)
        return bases

    def method_target(self, class_id: str, name: str, skip_current: bool = False) -> str | None:
        try:
            order = c3_linearize(class_id, self.class_bases())
        except ValueError:
            return None
        for owner in order[1:] if skip_current else order:
            target = self.own_method(owner, name)
            if target:
                return target
        return None

    def dispatch_order(self, class_id: str) -> list[str]:
        """Inspect the exact override precedence used for self and super calls."""
        return c3_linearize(class_id, self.class_bases())

    def dynamic_candidates(self, name: str) -> list[str]:
        """Potential same-name targets remain explicitly uncertain, never exact calls."""
        leaf = name.rsplit('.', 1)[-1]
        return sorted(
            symbol.id
            for symbol in self.symbols.values()
            if symbol.name == leaf and symbol.kind in {'function', 'method'}
        )

    def edge_confidence(self, name: str, target: str) -> float:
        # Local lexical binding is exact; method dispatch remains runtime-dependent.
        return 0.9 if name.startswith(('self.', 'cls.', 'super().')) else 1.0

    def structural_edges(self) -> list[Edge]:
        return [
            Edge(symbol.parent_id, symbol.id, kind)
            for symbol in self.symbols.values()
            if symbol.parent_id
            for kind in ('defines', 'contains')
        ]

    def save_graph(self, path: str | Path) -> None:
        import json
        import os
        from dataclasses import asdict
        from pathlib import Path

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(
                {'version': 1, 'edges': [asdict(edge) for edge in self.resolve()]},
                stream,
                sort_keys=True,
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    @staticmethod
    def load_edges(path: str | Path) -> list[Edge]:
        import json
        from pathlib import Path

        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('version') != 1:
            raise ValueError('Unsupported graph version')
        return [Edge(**edge) for edge in data['edges']]

    def import_edges(self) -> list[Edge]:
        edges = []
        for scope, alias in self.imports:
            target = self.resolve_import(alias, scope) or self.external_reference(alias, scope)
            edges.append(Edge(scope, target, 'imports', 1 if target in self.symbols else 0.5))
        return edges

    def inheritance_edges(self) -> list[Edge]:
        return [
            Edge(child, parent, 'inherits')
            for child, parents in self.class_bases().items()
            for parent in parents
        ]

    def test_associations(self, edges: list[Edge]) -> list[Edge]:
        """Associate test symbols through resolved calls, avoiding filename guesses."""
        from pathlib import PurePosixPath

        associations = []
        for edge in edges:
            source = self.symbols.get(edge.source)
            if edge.kind != 'calls' or edge.target not in self.symbols or not source:
                continue
            filename = PurePosixPath(source.path).name
            if source.name.startswith('test_') and (
                filename.startswith('test_') or filename.endswith('_test.py')
            ):
                associations.append(Edge(source.id, edge.target, 'tests', edge.confidence))
        return associations

    def callers(self, symbol_id: str, include_uncertain: bool = False) -> list[Symbol]:
        kinds = {'calls', 'may_call'} if include_uncertain else {'calls'}
        ids = {
            edge.source
            for edge in self.resolve()
            if edge.target == symbol_id and edge.kind in kinds
        }
        return sorted(
            (self.symbols[key] for key in ids if key in self.symbols), key=lambda s: s.qualname
        )

    def callees(self, symbol_id: str, include_uncertain: bool = False) -> list[Symbol]:
        kinds = {'calls', 'may_call'} if include_uncertain else {'calls'}
        ids = {
            edge.target
            for edge in self.resolve()
            if edge.source == symbol_id and edge.kind in kinds
        }
        return sorted(
            (self.symbols[key] for key in ids if key in self.symbols), key=lambda s: s.qualname
        )


def c3_linearize(
    class_id: str, bases: dict[str, list[str]], stack: tuple[str, ...] = ()
) -> list[str]:
    """Compute Python's C3 MRO and reject cyclic or inconsistent inheritance."""
    if class_id in stack:
        raise ValueError('Inheritance cycle')
    parents = bases.get(class_id, [])
    sequences = [c3_linearize(parent, bases, (*stack, class_id)) for parent in parents] + [
        list(parents)
    ]
    result = [class_id]
    while any(sequences):
        sequences = [sequence for sequence in sequences if sequence]
        candidate = next(
            (
                sequence[0]
                for sequence in sequences
                if all(sequence[0] not in other[1:] for other in sequences)
            ),
            None,
        )
        if candidate is None:
            raise ValueError('Inconsistent C3 inheritance order')
        result.append(candidate)
        for sequence in sequences:
            if sequence and sequence[0] == candidate:
                sequence.pop(0)
    return result


LABELLED_FIXTURE = {
    'source': 'def helper():\n    pass\ndef caller():\n    helper()\nclass Base:\n    def work(self):\n        pass\nclass Child(Base):\n    def run(self):\n        self.work()\n',
    'expected_calls': [
        ('fixture.caller', 'fixture.helper'),
        ('fixture.Child.run', 'fixture.Base.work'),
    ],
}


JEDI_REFERENCE_CASES = [
    ('def helper():\n    pass\ndef caller():\n    helper()\n', 4, 5, 'helper'),
    (
        'def outer():\n    def helper():\n        pass\n    def inner():\n        helper()\n',
        5,
        9,
        'helper',
    ),
    (
        'class Base:\n    def work(self):\n        pass\nclass Child(Base):\n    def run(self):\n        self.work()\n',
        6,
        14,
        'work',
    ),
]


def edge_metrics(
    actual: set[tuple[str, str]], expected: set[tuple[str, str]]
) -> dict[str, float | int]:
    true_positive = len(actual & expected)
    return {
        'true_positive': true_positive,
        'false_positive': len(actual - expected),
        'false_negative': len(expected - actual),
        'precision': true_positive / len(actual) if actual else (1.0 if not expected else 0.0),
        'recall': true_positive / len(expected) if expected else 1.0,
    }


RESOLUTION_LIMITATIONS = (
    'Runtime monkey-patching and decorators are not exact',
    'Declared-class self dispatch can differ from runtime subclass dispatch',
    'Unresolved external bases can change MRO',
    'Path-sensitive type inference, reflection and computed imports remain uncertain',
)
