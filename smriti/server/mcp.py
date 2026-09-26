"""Official MCP SDK adapter for local agent connections."""

from pathlib import Path

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

    return server
