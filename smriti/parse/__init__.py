"""Tree-sitter syntax extraction with byte-exact source ownership."""
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import PurePosixPath
from tree_sitter import Language, Parser, Tree
import tree_sitter_python
from smriti.models import Symbol


@dataclass
class ParseResult:
    path: str
    source: bytes
    tree: Tree
    symbols: list[Symbol] = field(default_factory=list)
    imports: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    inheritance: list = field(default_factory=list)
    diagnostics: list = field(default_factory=list)
    comprehensions: list = field(default_factory=list)


class SourceParser:
    def __init__(self):
        self.cache = {}
        self.parsers = {"python": Parser(Language(tree_sitter_python.language()))}

        import tree_sitter_typescript
        self.parsers["typescript"] = Parser(Language(tree_sitter_typescript.language_typescript()))

        import tree_sitter_java
        self.parsers["java"] = Parser(Language(tree_sitter_java.language()))

    def parse(self, path: str, source: bytes | str, language: str = "python") -> ParseResult:
        data = source.encode("utf-8") if isinstance(source, str) else source
        cached = self.cache.get(path)
        if cached is not None:
            old = cached.source
            prefix = 0
            while prefix < min(len(old), len(data)) and old[prefix] == data[prefix]:
                prefix += 1
            suffix = 0
            while suffix < min(len(old), len(data)) - prefix and old[-suffix - 1] == data[-suffix - 1]:
                suffix += 1
            old_end, new_end = len(old) - suffix, len(data) - suffix
            def point(source, position):
                before = source[:position]
                return (before.count(b"\n"), len(before.rsplit(b"\n", 1)[-1]))
            tree = cached.tree.copy()
            tree.edit(start_byte=prefix, old_end_byte=old_end, new_end_byte=new_end,
                start_point=point(old, prefix), old_end_point=point(old, old_end), new_end_point=point(data, new_end))
            tree = self.parsers[language].parse(data, tree)
        else:
            tree = self.parsers[language].parse(data)
        result = ParseResult(path.replace("\\", "/"), data, tree)
        self._extract(result, language)
        self.cache[path] = result
        return result

    def _extract(self, result: ParseResult, language: str) -> None:
        path = result.path
        name = PurePosixPath(path).stem
        module = str(PurePosixPath(path).with_suffix("")).replace("/", ".").removesuffix(".__init__")
        root = result.tree.root_node
        result.symbols.append(Symbol(sha256((path + ":module").encode()).hexdigest(), path, name,
            module, "module", 1, max(1, len(result.source.splitlines())), 0, len(result.source),
            body=result.source.decode("utf-8"), content_hash=sha256(result.source).hexdigest()))

        def walk(node, parent):
            if node.type in {"class_definition", "function_definition", "class_declaration", "function_declaration", "method_definition", "method_declaration", "constructor_declaration", "interface_declaration"} and node.child_by_field_name("name") and node.child_by_field_name("body"):
                kind = "class" if node.type in {"class_definition", "class_declaration", "interface_declaration"} else ("method" if parent.kind == "class" else "function")
                name_node = node.child_by_field_name("name")
                name = result.source[name_node.start_byte:name_node.end_byte].decode("utf-8")
                qualname = parent.qualname + "." + name
                body = result.source[node.start_byte:node.end_byte]
                body_node = node.child_by_field_name("body")
                signature = result.source[node.start_byte:body_node.start_byte].decode("utf-8").rstrip().rstrip(":")
                docstring = ""
                if body_node.named_children:
                    import ast
                    first = body_node.named_children[0]
                    try:
                        value = ast.literal_eval(result.source[first.start_byte:first.end_byte].decode("utf-8"))
                        if isinstance(value, str):
                            docstring = value
                    except (ValueError, SyntaxError):
                        pass
                symbol = Symbol(sha256((path + ":" + kind + ":" + qualname).encode()).hexdigest(), path,
                    name, qualname, kind, node.start_point.row + 1, node.end_point.row + 1,
                    node.start_byte, node.end_byte, signature=signature, docstring=docstring, body=body.decode("utf-8"),
                    content_hash=sha256(body).hexdigest(), parent_id=parent.id)
                result.symbols.append(symbol)
                if kind == "class":
                    bases = node.child_by_field_name("superclasses")
                    if bases:
                        for base in bases.named_children:
                            result.inheritance.append({"class": symbol.id, "scope": parent.id,
                                "name": result.source[base.start_byte:base.end_byte].decode("utf-8")})
                parent = symbol
            if language == "python" and node.type in {"import_statement", "import_from_statement"}:
                import ast
                statement = ast.parse(result.source[node.start_byte:node.end_byte].decode("utf-8")).body[0]
                for alias in statement.names:
                    module = statement.module or "" if isinstance(statement, ast.ImportFrom) else alias.name
                    level = statement.level if isinstance(statement, ast.ImportFrom) else 0
                    imported = alias.name if isinstance(statement, ast.ImportFrom) else ""
                    binding = alias.asname or (alias.name if imported else alias.name.split(".")[0])
                    result.imports.append({"scope": parent.id, "module": module, "name": imported,
                        "alias": binding, "level": level, "line": node.start_point.row + 1})
            if node.type == "call":
                function = node.child_by_field_name("function")
                result.calls.append({"scope": parent.id,
                    "name": result.source[function.start_byte:function.end_byte].decode("utf-8"),
                    "line": node.start_point.row + 1, "start_byte": node.start_byte})
            if node.type in {"list_comprehension", "set_comprehension", "dictionary_comprehension", "generator_expression"}:
                # Python comprehension targets are isolated from their enclosing scope.
                result.comprehensions.append({"parent": parent.id, "start_byte": node.start_byte,
                    "end_byte": node.end_byte, "source": result.source[node.start_byte:node.end_byte].decode("utf-8")})
            if node.type == "ERROR" or node.is_missing:
                result.diagnostics.append({"kind": "missing" if node.is_missing else "syntax_error",
                    "start_byte": node.start_byte, "end_byte": node.end_byte,
                    "line": node.start_point.row + 1})
            for child in node.named_children:
                walk(child, parent)
        walk(root, result.symbols[0])

def parse_file(path: str, source: bytes | str) -> ParseResult:
    return SourceParser().parse(path, source)


def source_slice(result: ParseResult, symbol: Symbol) -> bytes:
    """Ranges are UTF-8 byte offsets with an exclusive end, and 1-based lines."""
    return result.source[symbol.start_byte:symbol.end_byte]


def byte_point(source: bytes, position: int) -> tuple[int, int]:
    """Tree-sitter columns count bytes, including CR in CRLF line endings."""
    if not 0 <= position <= len(source):
        raise ValueError("Offset outside source")
    prefix = source[:position]
    return prefix.count(b"\n"), len(prefix.rsplit(b"\n", 1)[-1])


def symbol_chunks(result: ParseResult) -> list[tuple[str, bytes]]:
    """Independent source units follow definitions; modules only when no definitions exist."""
    definitions = [s for s in result.symbols if s.kind != "module"]
    return [(symbol.id, source_slice(result, symbol)) for symbol in definitions or result.symbols]


def split_oversized(source: bytes | str, max_bytes: int = 16384) -> list[bytes]:
    """Keep whole lines where possible; split long lines only at Unicode boundaries.

    Parts retain one anchor identity. Retrieval never invents new function identities.
    """
    if max_bytes < 4:
        raise ValueError("max_bytes must fit any UTF-8 code point")
    text = source.decode("utf-8") if isinstance(source, bytes) else source
    parts, current = [], b""
    for line in text.splitlines(keepends=True):
        encoded = line.encode("utf-8")
        if len(current) + len(encoded) <= max_bytes:
            current += encoded
            continue
        if current:
            parts.append(current)
            current = b""
        if len(encoded) <= max_bytes:
            current = encoded
        else:
            for char in line:
                value = char.encode("utf-8")
                if len(current) + len(value) > max_bytes:
                    parts.append(current)
                    current = b""
                current += value
    if current:
        parts.append(current)
    return parts


TYPESCRIPT_FIXTURE = "export class Worker { run(value: number): number { return value + 1; } }\nexport function launch(): Worker { return new Worker(); }"


JAVA_FIXTURE = "package demo; class Worker { int run(int value) { return value + 1; } }"


def validate_ranges(result: ParseResult) -> None:
    """Fail explicitly if an extraction range or its source content is inconsistent."""
    for symbol in result.symbols:
        if not 0 <= symbol.start_byte <= symbol.end_byte <= len(result.source):
            raise ValueError("Symbol byte range outside source")
        if source_slice(result, symbol).decode("utf-8") != symbol.body:
            raise ValueError("Symbol body disagrees with source range")
        actual = byte_point(result.source, symbol.start_byte)[0] + 1
        if actual != symbol.start_line:
            raise ValueError("Symbol line disagrees with source range")
