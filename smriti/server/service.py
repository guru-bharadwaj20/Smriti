"""Repository service shared by local command and agent interfaces."""

from dataclasses import dataclass
from pathlib import Path

from smriti.config import Config, load_config
from smriti.identity import repository_id
from smriti.merkle import RepositoryScanner
from smriti.models import Edge
from smriti.parse import ParseResult, SourceParser
from smriti.server.snapshots import IndexSnapshot, IndexStore


@dataclass(frozen=True)
class IndexResult:
    version: int
    files: int
    symbols: int
    changed_files: int
    diagnostics: tuple[str, ...]


class SmritiService:
    def __init__(self, root: Path, config: Config | None = None) -> None:
        self.config = config or load_config(root)
        self.root = self.config.root
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.repository = repository_id(self.root)
        self.store = IndexStore(self.config.data_dir / 'index.sqlite')
        self.parser = SourceParser()
        self._parsed: dict[str, ParseResult] = {}

    def snapshot(self) -> IndexSnapshot:
        return self.store.load()

    def index(self) -> IndexResult:
        previous = self.snapshot()
        ignored = ['.git', '.venv', '.smriti', '__pycache__', '.pytest_cache']
        if self.config.data_dir.is_relative_to(self.root):
            # The scanner excludes names at all depths. Custom state lives under
            # the first path component to prevent it recursively indexing itself.
            ignored.append(self.config.data_dir.relative_to(self.root).parts[0])
        scanned = RepositoryScanner(tuple(ignored)).scan(self.root)
        paths = {path: digest for path, digest in scanned.files.items()
                 if Path(path).suffix == '.py' and not (self.root / path).is_symlink()}
        changed = {path for path in paths.keys() | previous.files.keys()
                   if paths.get(path) != previous.files.get(path)}
        if not changed and previous.version:
            return IndexResult(previous.version, len(paths), len(previous.symbols), 0, ())
        for path in set(self._parsed) - paths.keys():
            del self._parsed[path]
        for path in paths:
            if path not in self._parsed or path in changed:
                self._parsed[path] = self.parser.parse(path, (self.root / path).read_bytes())
        symbols = tuple(symbol for path in sorted(self._parsed) for symbol in self._parsed[path].symbols)
        edges = tuple(Edge(symbol.parent_id, symbol.id, 'contains') for symbol in symbols
                      if symbol.parent_id is not None)
        version = self.store.publish(symbols, edges, paths, expected_version=previous.version)
        diagnostics = tuple(f'{path}: {diagnostic}' for path, result in self._parsed.items()
                            for diagnostic in result.diagnostics)
        return IndexResult(version, len(paths), len(symbols), len(changed), diagnostics)
