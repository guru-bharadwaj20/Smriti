"""Run the optional UI with a loopback-only listener."""

import argparse
from ipaddress import ip_address
from pathlib import Path

import uvicorn

from smriti.ui.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description='Inspect local Smriti context and memory.')
    parser.add_argument('root', nargs='?', default='.', type=Path)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()
    try:
        local = args.host == 'localhost' or ip_address(args.host).is_loopback
    except ValueError:
        local = False
    if not local:
        parser.error('The local UI requires a loopback host')
    if not 1 <= args.port <= 65535:
        parser.error('Port must be in 1..65535')
    if not args.root.is_dir():
        parser.error('Repository root must be an existing directory')
    uvicorn.run(create_app(args.root), host=args.host, port=args.port, proxy_headers=False)


if __name__ == '__main__':
    main()
