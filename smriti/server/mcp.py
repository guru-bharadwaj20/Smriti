"""Official MCP SDK adapter for local agent connections."""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from smriti import __version__
from smriti.server.service import SmritiService


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

    return server
