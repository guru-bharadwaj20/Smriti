"""Repository service shared by local command and agent interfaces."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from smriti.config import Config, load_config
from smriti.contracts import ContextResponse
from smriti.identity import repository_id
from smriti.merkle import RepositoryScanner
from smriti.models import Edge, Symbol
from smriti.parse import ParseResult, SourceParser
from smriti.resolve import Resolver
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
        self._retrieval: object | None = None

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
        languages = {'.py': 'python', '.ts': 'typescript', '.java': 'java'}
        paths = {
            path: digest
            for path, digest in scanned.files.items()
            if Path(path).suffix in languages and not (self.root / path).is_symlink()
        }
        changed = {
            path
            for path in paths.keys() | previous.files.keys()
            if paths.get(path) != previous.files.get(path)
        }
        if not changed and previous.version:
            return IndexResult(previous.version, len(paths), len(previous.symbols), 0, ())
        for path in set(self._parsed) - paths.keys():
            del self._parsed[path]
        for path in paths:
            if path not in self._parsed or path in changed:
                self._parsed[path] = self.parser.parse(
                    path, (self.root / path).read_bytes(), languages[Path(path).suffix]
                )
        source_symbols = tuple(
            symbol for path in sorted(self._parsed) for symbol in self._parsed[path].symbols
        )
        resolved = Resolver(list(self._parsed.values())).resolve()
        source_ids = {symbol.id for symbol in source_symbols}
        external_ids = {edge.target for edge in resolved if edge.target not in source_ids}
        external_symbols = tuple(
            Symbol(
                identity,
                '<external>',
                identity.rsplit(':', 1)[-1],
                identity,
                'variable',
                content_hash=sha256(identity.encode()).hexdigest(),
            )
            for identity in sorted(external_ids)
        )
        symbols = (*source_symbols, *external_symbols)
        edges = tuple(
            set(resolved)
            | {
                Edge(symbol.parent_id, symbol.id, 'contains')
                for symbol in source_symbols
                if symbol.parent_id is not None
            }
        )
        version = self.store.publish(symbols, edges, paths, expected_version=previous.version)
        diagnostics = tuple(
            f'{path}: {diagnostic}'
            for path, result in self._parsed.items()
            for diagnostic in result.diagnostics
        )
        return IndexResult(version, len(paths), len(symbols), len(changed), diagnostics)

    def find_symbol(self, name: str) -> list[Symbol]:
        query = name.casefold()
        return sorted(
            (
                symbol
                for symbol in self.snapshot().symbols
                if query in symbol.name.casefold()
                or query in symbol.qualname.casefold()
                or name == symbol.id
            ),
            key=lambda symbol: (symbol.path, symbol.start_line, symbol.id),
        )

    def context(self, task: str, budget: int | None = None) -> ContextResponse:
        from smriti.server.retrieval import Retriever
        from smriti.server.schemas import ContextRequest

        request = ContextRequest(task=task, budget=self.config.budget if budget is None else budget)
        snapshot = self.snapshot()
        if (
            not isinstance(self._retrieval, Retriever)
            or self._retrieval.snapshot.version != snapshot.version
        ):
            self._retrieval = Retriever(
                snapshot, self.config.tokenizer, self.config.model_dir, self.config.data_dir
            )
        return self._retrieval.context(request.task, request.budget)

    def calls(self, name: str, *, incoming: bool) -> list[Edge]:
        """Return possible and resolved calls for matching definitions."""
        identities = {symbol.id for symbol in self.find_symbol(name)}
        return sorted(
            (
                edge
                for edge in self.snapshot().edges
                if edge.kind in {'calls', 'may_call'}
                and (edge.target if incoming else edge.source) in identities
            ),
            key=lambda edge: (edge.source, edge.target, edge.kind, edge.confidence),
        )


class MemoryService:
    """Validated memory operations shared by the CLI and MCP adapters."""

    def __init__(self, root: Path, config: Config | None = None) -> None:
        from smriti.memory import MemoryStore

        self.config = config or load_config(root)
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.store = MemoryStore(self.config.data_dir / 'memory.sqlite')

    def close(self) -> None:
        self.store.close()

    def remember(
        self,
        fact: str,
        *,
        anchors: list[dict[str, str]] | None = None,
        confidence: float = 1.0,
        source: str | None = None,
        session: str | None = None,
    ) -> dict[str, Any]:
        from smriti.memory import Anchor
        from smriti.server.schemas import RememberRequest

        request = RememberRequest.model_validate(
            {
                'fact': fact,
                'anchors': anchors or [],
                'confidence': float(confidence),
                'source': source,
                'session': session,
            }
        )
        return self.store.remember(
            request.fact,
            anchors=[Anchor(a.symbol_id, a.content_hash) for a in request.anchors],
            confidence=request.confidence,
            source=request.source,
            session=request.session,
        ).to_dict()

    def recall(self, query: str = '', include_stale: bool = True) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self.store.recall(query, include_stale=include_stale)]

    def forget(
        self, *, fact_id: str | None = None, source: str | None = None, session: str | None = None
    ) -> list[str]:
        from smriti.server.schemas import ForgetRequest

        request = ForgetRequest(fact_id=fact_id, source=source, session=session)
        if request.fact_id is not None:
            return self.store.forget(request.fact_id)
        return self.store.forget_by(session=request.session, source=request.source)

    def log(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self.store.log(limit=limit)

    def diff(self, left: str | None, right: str | None = None) -> dict[str, Any]:
        return self.store.diff(left, right)

    def revert(self, operation_id: str) -> str:
        return self.store.revert(operation_id)

    def branch(self, name: str, switch: bool = False) -> dict[str, Any]:
        self.store.branch(name)
        if switch:
            self.store.switch(name)
        return {'branch': self.store.current_branch, 'branches': self.store.branches()}

    def switch(self, name: str) -> dict[str, Any]:
        self.store.switch(name)
        return {'branch': self.store.current_branch, 'head': self.store.head}

    def merge(self, source: str, resolutions: dict[str, str] | None = None) -> dict[str, Any]:
        from smriti.memory import MergeConflict
        from smriti.server.schemas import MergeRequest

        request = MergeRequest.model_validate({'source': source, 'resolutions': resolutions or {}})
        try:
            operation = self.store.merge(request.source, resolutions=dict(request.resolutions))
        except MergeConflict as conflict:
            return {'merged': False, 'conflicts': conflict.conflicts}
        return {'merged': True, 'operation': operation}
