"""Official MCP SDK adapter for local agent connections."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from smriti import __version__
from smriti.server.service import MemoryService, SmritiService


def create_server(root: Path) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(
        'smriti', version=__version__, instructions='Local code context and versioned memory.'
    )
    service = SmritiService(root)

    @server.tool()
    def context(task: str, budget: int = 8000) -> str:
        """Retrieve source and explanations within the requested token budget."""
        return service.context(task, budget).text

    @server.tool()
    def status() -> dict[str, int | bool]:
        """Read the committed repository index status."""
        from dataclasses import asdict

        from smriti.server.status import index_status

        return asdict(index_status(root))

    @server.tool()
    def find_symbol(name: str) -> list[dict[str, Any]]:
        """Find indexed definitions by name, qualified name, or symbol ID."""
        return [asdict(symbol) for symbol in service.find_symbol(name)]

    @server.tool()
    def callers(name: str) -> list[dict[str, Any]]:
        """List call edges targeting matching definitions."""
        return [asdict(edge) for edge in service.calls(name, incoming=True)]

    @server.tool()
    def callees(name: str) -> list[dict[str, Any]]:
        """List call edges originating in matching definitions."""
        return [asdict(edge) for edge in service.calls(name, incoming=False)]

    def memory() -> MemoryService:
        return MemoryService(root)

    @server.tool()
    def remember(
        fact: str,
        anchors: list[dict[str, str]] | None = None,
        confidence: float = 1.0,
        source: str | None = None,
        session: str | None = None,
    ) -> dict[str, Any]:
        """Record a project or symbol-anchored fact."""
        store = memory()
        try:
            return store.remember(
                fact, anchors=anchors, confidence=confidence, source=source, session=session
            )
        finally:
            store.close()

    @server.tool()
    def recall(query: str = '', include_stale: bool = True) -> list[dict[str, Any]]:
        """Recall facts with freshness and provenance."""
        store = memory()
        try:
            return store.recall(query, include_stale)
        finally:
            store.close()

    @server.tool()
    def forget(
        fact_id: str | None = None, source: str | None = None, session: str | None = None
    ) -> list[str]:
        """Purge one fact, source, or session together with derived facts."""
        store = memory()
        try:
            return store.forget(fact_id=fact_id, source=source, session=session)
        finally:
            store.close()

    @server.tool()
    def memory_log(limit: int | None = None) -> list[dict[str, Any]]:
        """List memory operations on the active branch, newest first."""
        store = memory()
        try:
            return store.log(limit)
        finally:
            store.close()

    @server.tool()
    def memory_diff(left: str | None = None, right: str | None = None) -> dict[str, Any]:
        """Compare memory states between two operations."""
        store = memory()
        try:
            return store.diff(left, right)
        finally:
            store.close()

    @server.tool()
    def memory_revert(operation_id: str) -> str:
        """Append an inverse of an earlier operation."""
        store = memory()
        try:
            return store.revert(operation_id)
        finally:
            store.close()

    @server.tool()
    def memory_branch(name: str, switch: bool = False) -> dict[str, Any]:
        """Create a memory branch, optionally switching to it."""
        store = memory()
        try:
            return store.branch(name, switch)
        finally:
            store.close()

    @server.tool()
    def memory_switch(name: str) -> dict[str, Any]:
        """Switch the active memory branch."""
        store = memory()
        try:
            return store.switch(name)
        finally:
            store.close()

    @server.tool()
    def memory_merge(source: str, resolutions: dict[str, str] | None = None) -> dict[str, Any]:
        """Merge a memory branch, reporting unresolved conflicts."""
        store = memory()
        try:
            return store.merge(source, resolutions)
        finally:
            store.close()

    return server
