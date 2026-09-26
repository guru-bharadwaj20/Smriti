"""Official MCP SDK adapter for local agent connections."""

from pathlib import Path

from mcp.server import MCPServer

from smriti import __version__


def create_server(root: Path) -> MCPServer[None]:
    server: MCPServer[None] = MCPServer(
        'smriti', version=__version__, instructions='Local code context and versioned memory.'
    )

    @server.tool()
    def status() -> dict[str, int | bool]:
        """Read the committed repository index status."""
        from dataclasses import asdict

        from smriti.server.status import index_status

        return asdict(index_status(root))

    return server
