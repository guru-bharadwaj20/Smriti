"""Smoke-test an installed Smriti: console script, CLI round trip and MCP stdio.

Run with the interpreter of the environment under test, outside the source tree:
``python scripts/smoke_install.py``. Exits non-zero on the first failure.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = 'def parse_header(line):\n    return line.split(":", 1)\n\n\ndef load(text):\n    return [parse_header(x) for x in text.splitlines()]\n'


def cli(executable: str, *args: str) -> str:
    result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise SystemExit(f'smriti {" ".join(args)} failed:\n{result.stderr}')
    return result.stdout


async def mcp(executable: str, root: Path) -> list[str]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=executable, args=['serve', '--root', str(root)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = sorted(tool.name for tool in (await session.list_tools()).tools)
            found = await session.call_tool('find_symbol', {'name': 'parse_header'})
            if found.is_error or 'app.py' not in found.content[0].text:
                raise SystemExit('MCP find_symbol failed')
            context = await session.call_tool('context', {'task': 'parse header', 'budget': 500})
            if context.is_error or 'parse_header' not in context.content[0].text:
                raise SystemExit('MCP context failed')
            return tools


def main() -> None:
    import smriti

    location = Path(smriti.__file__).resolve()
    if Path.cwd().resolve() in location.parents and (Path.cwd() / 'pyproject.toml').exists():
        raise SystemExit('Run outside the source tree so the installed package is tested')
    executable = shutil.which('smriti', path=os.path.dirname(sys.executable)) or shutil.which(
        'smriti', path=str(Path(sys.executable).parent / 'Scripts')
    )
    if executable is None:
        raise SystemExit('smriti console script is not installed next to this interpreter')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'app.py').write_text(SOURCE)
        version = cli(executable, 'version').strip()
        cli(executable, 'index', '--root', str(root))
        found = json.loads(cli(executable, 'find-symbol', 'parse_header', '--root', str(root)))
        callers = json.loads(cli(executable, 'callers', 'parse_header', '--root', str(root)))
        loader = json.loads(cli(executable, 'find-symbol', 'load', '--root', str(root)))
        context = cli(executable, 'context', 'parse header', '--budget', '500', '--root', str(root))
        fact = json.loads(cli(executable, 'remember', 'headers split once', '--root', str(root)))
        recalled = json.loads(cli(executable, 'recall', 'headers', '--root', str(root)))
        assert found and found[0]['name'] == 'parse_header', found
        assert [edge['source'] for edge in callers] == [loader[0]['id']], callers
        assert 'parse_header' in context
        assert recalled and recalled[0]['id'] == fact['id'], recalled
        tools = asyncio.run(mcp(executable, root))
    print(json.dumps({'version': version, 'package': str(location.parent), 'mcp_tools': tools}))


if __name__ == '__main__':
    main()
