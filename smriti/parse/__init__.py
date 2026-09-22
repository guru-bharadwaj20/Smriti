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


def parse_file(path: str, source: bytes | str) -> ParseResult:
    return SourceParser().parse(path, source)
