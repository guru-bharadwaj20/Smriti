import asyncio
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def run_tools(root: Path, calls: list[tuple[str, dict[str, Any]]]) -> list[Any]:
    async def run() -> list[Any]:
        params = StdioServerParameters(
            command=sys.executable,
            args=['-m', 'smriti', 'serve', '--root', str(root)],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        results = []
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                for name, arguments in calls:
                    result = await session.call_tool(name, arguments)
                    results.append(result)
        return results

    return asyncio.run(run())


def test_symbol_and_graph_tools(tmp_path: Path) -> None:
    from smriti.server.service import SmritiService

    (tmp_path / 'm.py').write_text('def a():\n    return b()\n\n\ndef b():\n    return 1\n')
    SmritiService(tmp_path).index()
    found, incoming, outgoing = run_tools(
        tmp_path,
        [('find_symbol', {'name': 'b'}), ('callers', {'name': 'b'}), ('callees', {'name': 'a'})],
    )
    assert not found.is_error and 'm.py' in found.content[0].text
    assert not incoming.is_error and 'calls' in incoming.content[0].text
    assert not outgoing.is_error and 'calls' in outgoing.content[0].text


def test_memory_crud_tools(tmp_path: Path) -> None:
    remembered, recalled, forgotten, empty, invalid = run_tools(
        tmp_path,
        [
            ('remember', {'fact': 'Use the cache', 'source': 'notes'}),
            ('recall', {'query': 'cache'}),
            ('forget', {'source': 'notes'}),
            ('recall', {}),
            ('forget', {}),
        ],
    )
    assert not remembered.is_error and 'Use the cache' in remembered.content[0].text
    assert 'Use the cache' in recalled.content[0].text
    assert not forgotten.is_error
    assert empty.content == [] or 'Use the cache' not in empty.content[0].text
    assert invalid.is_error


def test_memory_history_tools(tmp_path: Path) -> None:
    results = run_tools(
        tmp_path,
        [
            ('remember', {'fact': 'Base'}),
            ('memory_branch', {'name': 'feature', 'switch': True}),
            ('remember', {'fact': 'Feature'}),
            ('memory_switch', {'name': 'main'}),
            ('memory_merge', {'source': 'feature'}),
            ('memory_log', {'limit': 1}),
            ('memory_diff', {}),
        ],
    )
    assert not any(result.is_error for result in results)
    assert results[4].structured_content['merged'] is True
    assert 'Feature' in results[6].content[0].text
    operation = results[5].structured_content['result'][0]['id']
    reverted = run_tools(tmp_path, [('memory_revert', {'operation_id': operation})])[0]
    assert not reverted.is_error
