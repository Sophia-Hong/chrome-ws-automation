#!/usr/bin/env python3
"""
Programmatic client for the Browser Automation Bridge.
Use this from scripts or OpenClaw exec calls.

Usage:
    python client.py navigate "https://reddit.com/r/tenants"
    python client.py snapshot
    python client.py getText "h1"
    python client.py click ".search-button"
    python client.py getLinks "reddit"
"""

import asyncio
import json
import sys
import uuid

try:
    import websockets
except ImportError:
    print("pip install websockets")
    sys.exit(1)

WS_URL = "ws://localhost:9876"


async def send_command(command: str, params: dict) -> dict:
    """Connect to the bridge server and send a single command."""
    # Connect as a "controller" — the server treats us like the extension
    # Actually, we need a separate endpoint. For now, use a simple HTTP-like approach:
    # Send command via a temporary WebSocket connection.
    
    # For the MVP, we'll talk directly to the bridge server
    # The bridge server needs a second endpoint for controllers.
    # Simpler approach: use stdin/stdout pipe to bridge.py
    
    # For now: direct WebSocket to bridge, tagged as controller
    async with websockets.connect(WS_URL) as ws:
        msg_id = str(uuid.uuid4())[:8]
        await ws.send(json.dumps({
            "type": "controller",
            "id": msg_id,
            "command": command,
            "params": params,
        }))
        response = await asyncio.wait_for(ws.recv(), timeout=30)
        return json.loads(response)


def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <command> [params_json_or_arg]")
        print("Commands: navigate, click, fill, getText, getLinks, evaluate, snapshot, tabs")
        sys.exit(1)

    command = sys.argv[1]
    
    # Parse params
    params = {}
    if len(sys.argv) > 2:
        rest = sys.argv[2]
        try:
            params = json.loads(rest)
        except json.JSONDecodeError:
            # Smart param inference
            if command == "navigate":
                params = {"url": rest}
            elif command in ("click", "getText", "waitForSelector", "scroll"):
                params = {"selector": rest}
            elif command == "fill":
                params = {"selector": rest, "value": sys.argv[3] if len(sys.argv) > 3 else ""}
            elif command == "evaluate":
                params = {"expression": rest}
            elif command == "getLinks":
                params = {"filter": rest}
            else:
                params = {"arg": rest}

    result = asyncio.run(send_command(command, params))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
