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


class SourceParser:
    def __init__(self):
        self.parsers = {"python": Parser(Language(tree_sitter_python.language()))}

    def parse(self, path: str, source: bytes | str, language: str = "python") -> ParseResult:
        data = source.encode("utf-8") if isinstance(source, str) else source
        tree = self.parsers[language].parse(data)
        result = ParseResult(path.replace("\\", "/"), data, tree)
        self._extract(result, language)
        return result

    def _extract(self, result: ParseResult, language: str) -> None:
        path = result.path
        name = PurePosixPath(path).stem
        module = path.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
        root = result.tree.root_node
        result.symbols.append(Symbol(sha256((path + ":module").encode()).hexdigest(), path, name,
            module, "module", 1, max(1, len(result.source.splitlines())), 0, len(result.source),
            body=result.source.decode("utf-8"), content_hash=sha256(result.source).hexdigest()))

        def walk(node, parent):
            if node.type in {"class_definition", "function_definition"}:
                kind = "class" if node.type == "class_definition" else ("method" if parent.kind == "class" else "function")
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
                parent = symbol
            for child in node.named_children:
                walk(child, parent)
        walk(root, result.symbols[0])

def parse_file(path: str, source: bytes | str) -> ParseResult:
    return SourceParser().parse(path, source)
