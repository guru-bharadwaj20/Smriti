import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_official_stdio_handshake_and_tool(tmp_path: Path) -> None:
    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=['-m', 'smriti', 'serve', '--root', str(tmp_path)],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert initialized.server_info.name == 'smriti'
                assert 'status' in {tool.name for tool in (await session.list_tools()).tools}
                result = await session.call_tool('status', {})
                assert not result.is_error
                assert result.structured_content is not None
                assert result.structured_content['indexed'] is False

    asyncio.run(run())
