#!/usr/bin/env python3
"""
One-shot CLI for browser automation.
Usage: python cli.py <command> [args...]

Examples:
  python cli.py navigate https://reddit.com
  python cli.py snapshot
  python cli.py click "button.submit"
  python cli.py fill "input[name=q]" "search term"
  python cli.py evaluate "document.title"
  python cli.py getText ".main-content"
  python cli.py getLinks
  python cli.py getTabs
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("pip install websockets")
    sys.exit(1)

WS_URL = "ws://localhost:9876"


async def oneshot(command: str, params: dict) -> dict:
    """Connect to running server and send one command."""
    async with websockets.connect(WS_URL) as ws:
        msg = {"id": "cli", "command": command, "params": params}
        await ws.send(json.dumps(msg))
        resp = await asyncio.wait_for(ws.recv(), timeout=30)
        return json.loads(resp)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    params = {}

    if cmd == "navigate" and len(sys.argv) > 2:
        params["url"] = sys.argv[2]
    elif cmd == "click" and len(sys.argv) > 2:
        params["selector"] = sys.argv[2]
    elif cmd == "fill" and len(sys.argv) > 3:
        params["selector"] = sys.argv[2]
        params["value"] = sys.argv[3]
    elif cmd == "evaluate" and len(sys.argv) > 2:
        params["expression"] = " ".join(sys.argv[2:])
    elif cmd == "getText" and len(sys.argv) > 2:
        params["selector"] = sys.argv[2]

    result = asyncio.run(oneshot(cmd, params))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
