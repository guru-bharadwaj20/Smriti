"""Tree-sitter syntax extraction with byte-exact source ownership."""

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import PurePosixPath
from typing import TypedDict

import tree_sitter_python
from tree_sitter import Language, Node, Parser, Tree

from smriti.models import Symbol, SymbolKind


class ImportDeclaration(TypedDict):
    scope: str
    module: str
    name: str
    alias: str
    level: int
    line: int


class CallCandidate(TypedDict):
    scope: str
    name: str
    line: int
    start_byte: int


InheritanceDeclaration = TypedDict(
    'InheritanceDeclaration', {'class': str, 'scope': str, 'name': str}
)


class ParseDiagnostic(TypedDict):
    kind: str
    start_byte: int
    end_byte: int
    line: int


class ComprehensionScope(TypedDict):
    parent: str
    start_byte: int
    end_byte: int
    source: str


@dataclass
class ParseResult:
    path: str
    source: bytes
    tree: Tree
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportDeclaration] = field(default_factory=list)
    calls: list[CallCandidate] = field(default_factory=list)
    inheritance: list[InheritanceDeclaration] = field(default_factory=list)
    diagnostics: list[ParseDiagnostic] = field(default_factory=list)
    comprehensions: list[ComprehensionScope] = field(default_factory=list)
    language: str = 'python'
    package: str = ''
    receiver_bindings: dict[str, tuple[str, str]] = field(default_factory=dict)
    local_names: dict[str, set[str]] = field(default_factory=dict)


class SourceParser:
    def __init__(self) -> None:
        self.cache: dict[str, ParseResult] = {}
        self.parsers = {'python': Parser(Language(tree_sitter_python.language()))}

        import tree_sitter_typescript

        self.parsers['typescript'] = Parser(Language(tree_sitter_typescript.language_typescript()))

        import tree_sitter_java

        self.parsers['java'] = Parser(Language(tree_sitter_java.language()))
        import tree_sitter_c
        import tree_sitter_cpp
        import tree_sitter_go

        for name, grammar in (
            ('go', tree_sitter_go),
            ('c', tree_sitter_c),
            ('cpp', tree_sitter_cpp),
        ):
            self.parsers[name] = Parser(Language(grammar.language()))

    def parse(self, path: str, source: bytes | str, language: str = 'python') -> ParseResult:
        data = source.encode('utf-8') if isinstance(source, str) else source
        cached = self.cache.get(path)
        if cached is not None and cached.language != language:
            cached = None
        if cached is not None:
            old = cached.source
            prefix = 0
            while prefix < min(len(old), len(data)) and old[prefix] == data[prefix]:
                prefix += 1
            suffix = 0
            while (
                suffix < min(len(old), len(data)) - prefix and old[-suffix - 1] == data[-suffix - 1]
            ):
                suffix += 1
            old_end, new_end = len(old) - suffix, len(data) - suffix

            def point(source: bytes, position: int) -> tuple[int, int]:
                before = source[:position]
                return (before.count(b'\n'), len(before.rsplit(b'\n', 1)[-1]))

            tree = cached.tree.copy()
            tree.edit(
                start_byte=prefix,
                old_end_byte=old_end,
                new_end_byte=new_end,
                start_point=point(old, prefix),
                old_end_point=point(old, old_end),
                new_end_point=point(data, new_end),
            )
            tree = self.parsers[language].parse(data, tree)
        else:
            tree = self.parsers[language].parse(data)
        result = ParseResult(path.replace('\\', '/'), data, tree)
        result.language = language
        self._extract(result, language)
        self.cache[path] = result
        return result

    def _extract(self, result: ParseResult, language: str) -> None:
        if language in {'go', 'c', 'cpp'}:
            from .languages import extract

            extract(result)
            return
        path = result.path
        name = PurePosixPath(path).stem
        module = (
            str(PurePosixPath(path).with_suffix('')).replace('/', '.').removesuffix('.__init__')
        )
        root = result.tree.root_node
        result.symbols.append(
            Symbol(
                sha256((path + ':module').encode()).hexdigest(),
                path,
                name,
                module,
                'module',
                1,
                max(1, len(result.source.splitlines())),
                0,
                len(result.source),
                body=result.source.decode('utf-8', 'replace'),
                content_hash=sha256(result.source).hexdigest(),
            )
        )

        def visit(node: Node, parent: Symbol) -> Symbol:
            if (
                node.type
                in {
                    'class_definition',
                    'function_definition',
                    'class_declaration',
                    'function_declaration',
                    'method_definition',
                    'method_declaration',
                    'constructor_declaration',
                    'interface_declaration',
                }
                and node.child_by_field_name('name')
                and node.child_by_field_name('body')
            ):
                kind: SymbolKind = (
                    'class'
                    if node.type
                    in {'class_definition', 'class_declaration', 'interface_declaration'}
                    else ('method' if parent.kind == 'class' else 'function')
                )
                name_node = node.child_by_field_name('name')
                assert name_node is not None
                name = result.source[name_node.start_byte : name_node.end_byte].decode(
                    'utf-8', 'replace'
                )
                qualname = parent.qualname + '.' + name
                source_node = (
                    node.parent
                    if node.parent is not None and node.parent.type == 'decorated_definition'
                    else node
                )
                body = result.source[source_node.start_byte : node.end_byte]
                body_node = node.child_by_field_name('body')
                assert body_node is not None
                signature = (
                    result.source[source_node.start_byte : body_node.start_byte]
                    .decode('utf-8', 'replace')
                    .rstrip()
                    .rstrip(':')
                )
                docstring = ''
                if body_node.named_children:
                    import ast

                    first = body_node.named_children[0]
                    try:
                        value = ast.literal_eval(
                            result.source[first.start_byte : first.end_byte].decode(
                                'utf-8', 'replace'
                            )
                        )
                        if isinstance(value, str):
                            docstring = value
                    except (ValueError, SyntaxError, RecursionError, MemoryError):
                        pass
                symbol = Symbol(
                    sha256((path + ':' + kind + ':' + qualname).encode()).hexdigest(),
                    path,
                    name,
                    qualname,
                    kind,
                    source_node.start_point.row + 1,
                    node.end_point.row + 1,
                    source_node.start_byte,
                    node.end_byte,
                    signature=signature,
                    docstring=docstring,
                    body=body.decode('utf-8', 'replace'),
                    content_hash=sha256(body).hexdigest(),
                    parent_id=parent.id,
                )
                result.symbols.append(symbol)
                if kind == 'class':
                    bases = node.child_by_field_name('superclasses')
                    if bases:
                        for base in bases.named_children:
                            result.inheritance.append(
                                {
                                    'class': symbol.id,
                                    'scope': parent.id,
                                    'name': result.source[base.start_byte : base.end_byte].decode(
                                        'utf-8', 'replace'
                                    ),
                                }
                            )
                parent = symbol
            if language == 'python' and node.type in {'import_statement', 'import_from_statement'}:
                import ast

                statement = ast.parse(
                    result.source[node.start_byte : node.end_byte].decode('utf-8', 'replace')
                ).body[0]
                assert isinstance(statement, (ast.Import, ast.ImportFrom))
                for alias in statement.names:
                    module = (
                        statement.module or ''
                        if isinstance(statement, ast.ImportFrom)
                        else alias.name
                    )
                    level = statement.level if isinstance(statement, ast.ImportFrom) else 0
                    imported = alias.name if isinstance(statement, ast.ImportFrom) else ''
                    binding = alias.asname or (alias.name if imported else alias.name.split('.')[0])
                    result.imports.append(
                        {
                            'scope': parent.id,
                            'module': module,
                            'name': imported,
                            'alias': binding,
                            'level': level,
                            'line': node.start_point.row + 1,
                        }
                    )
            if node.type == 'call':
                function = node.child_by_field_name('function')
                assert function is not None
                result.calls.append(
                    {
                        'scope': parent.id,
                        'name': result.source[function.start_byte : function.end_byte].decode(
                            'utf-8', 'replace'
                        ),
                        'line': node.start_point.row + 1,
                        'start_byte': node.start_byte,
                    }
                )
            if node.type in {
                'list_comprehension',
                'set_comprehension',
                'dictionary_comprehension',
                'generator_expression',
            }:
                # Python comprehension targets are isolated from their enclosing scope.
                result.comprehensions.append(
                    {
                        'parent': parent.id,
                        'start_byte': node.start_byte,
                        'end_byte': node.end_byte,
                        'source': result.source[node.start_byte : node.end_byte].decode(
                            'utf-8', 'replace'
                        ),
                    }
                )
            if node.type == 'ERROR' or node.is_missing:
                result.diagnostics.append(
                    {
                        'kind': 'missing' if node.is_missing else 'syntax_error',
                        'start_byte': node.start_byte,
                        'end_byte': node.end_byte,
                        'line': node.start_point.row + 1,
                    }
                )
            return parent

        # Explicit stack instead of recursion: generated or deeply nested code
        # (e.g. astropy's parser tables) exceeds Python's recursion limit. Pushing
        # children in reverse keeps the same pre-order visit as recursive descent.
        stack: list[tuple[Node, Symbol]] = [(root, result.symbols[0])]
        while stack:
            node, parent = stack.pop()
            scope = visit(node, parent)
            stack.extend((child, scope) for child in reversed(node.named_children))


def parse_file(path: str, source: bytes | str) -> ParseResult:
    return SourceParser().parse(path, source)


def source_slice(result: ParseResult, symbol: Symbol) -> bytes:
    """Ranges are UTF-8 byte offsets with an exclusive end, and 1-based lines."""
    return result.source[symbol.start_byte : symbol.end_byte]


def byte_point(source: bytes, position: int) -> tuple[int, int]:
    """Tree-sitter columns count bytes, including CR in CRLF line endings."""
    if not 0 <= position <= len(source):
        raise ValueError('Offset outside source')
    prefix = source[:position]
    return prefix.count(b'\n'), len(prefix.rsplit(b'\n', 1)[-1])


def symbol_chunks(result: ParseResult) -> list[tuple[str, bytes]]:
    """Independent source units follow definitions; modules only when no definitions exist."""
    definitions = [s for s in result.symbols if s.kind != 'module']
    return [(symbol.id, source_slice(result, symbol)) for symbol in definitions or result.symbols]


def split_oversized(source: bytes | str, max_bytes: int = 16384) -> list[bytes]:
    """Keep whole lines where possible; split long lines only at Unicode boundaries.

    Parts retain one anchor identity. Retrieval never invents new function identities.
    """
    if max_bytes < 4:
        raise ValueError('max_bytes must fit any UTF-8 code point')
    text = source.decode('utf-8', 'replace') if isinstance(source, bytes) else source
    parts, current = [], b''
    for line in text.splitlines(keepends=True):
        encoded = line.encode('utf-8')
        if len(current) + len(encoded) <= max_bytes:
            current += encoded
            continue
        if current:
            parts.append(current)
            current = b''
        if len(encoded) <= max_bytes:
            current = encoded
        else:
            for char in line:
                value = char.encode('utf-8')
                if len(current) + len(value) > max_bytes:
                    parts.append(current)
                    current = b''
                current += value
    if current:
        parts.append(current)
    return parts


TYPESCRIPT_FIXTURE = 'export class Worker { run(value: number): number { return value + 1; } }\nexport function launch(): Worker { return new Worker(); }'


JAVA_FIXTURE = 'package demo; class Worker { int run(int value) { return value + 1; } }'


def validate_ranges(result: ParseResult) -> None:
    """Fail explicitly if an extraction range or its source content is inconsistent."""
    for symbol in result.symbols:
        if not 0 <= symbol.start_byte <= symbol.end_byte <= len(result.source):
            raise ValueError('Symbol byte range outside source')
        if source_slice(result, symbol).decode('utf-8', 'replace') != symbol.body:
            raise ValueError('Symbol body disagrees with source range')
        actual = byte_point(result.source, symbol.start_byte)[0] + 1
        if actual != symbol.start_line:
            raise ValueError('Symbol line disagrees with source range')


LANGUAGE_SUPPORT = {
    'python': 'Definitions, imports, calls, inheritance and incremental trees',
    'typescript': 'Definitions and methods; full type-based call resolution is deferred',
    'java': 'Definitions and methods; full overload resolution is deferred',
    'go': 'Definitions, imports, receiver methods, conservative package calls',
    'c': 'Definitions, includes and conservative direct calls; no macro expansion',
    'cpp': 'Namespaces, classes and direct calls; unresolved overloads remain uncertain',
}
