#!/usr/bin/env python3
"""
Browser Automation Bridge — WebSocket server.
Chrome Extension connects as the executor. Python clients connect as controllers.
"""

import asyncio
import json
import sys
import uuid
from typing import Optional

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("pip install websockets")
    sys.exit(1)

HOST = "localhost"
PORT = 9876

extension_ws = None
pending: dict[str, asyncio.Future] = {}


async def send_to_extension(command: str, params: Optional[dict] = None, timeout: float = 30.0) -> dict:
    if not extension_ws:
        raise ConnectionError("No Chrome extension connected")
    msg_id = str(uuid.uuid4())[:8]
    future = asyncio.get_event_loop().create_future()
    pending[msg_id] = future
    await extension_ws.send(json.dumps({"id": msg_id, "command": command, "params": params or {}}))
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        pending.pop(msg_id, None)


async def handle_connection(websocket):
    global extension_ws

    # First message determines role
    raw = await websocket.recv()
    msg = json.loads(raw)

    if msg.get("type") == "hello" and msg.get("agent") == "chrome-extension":
        # This is the extension
        extension_ws = websocket
        print("[bridge] Extension connected")
        try:
            async for raw in websocket:
                data = json.loads(raw)
                msg_id = data.get("id")
                if msg_id and msg_id in pending:
                    pending[msg_id].set_result(data)
        except websockets.ConnectionClosed:
            pass
        finally:
            extension_ws = None
            print("[bridge] Extension disconnected")

    elif msg.get("type") == "controller":
        # This is a controller client
        command = msg.get("command")
        params = msg.get("params", {})
        msg_id = msg.get("id", str(uuid.uuid4())[:8])
        try:
            result = await send_to_extension(command, params)
            await websocket.send(json.dumps(result))
        except Exception as e:
            await websocket.send(json.dumps({"id": msg_id, "error": str(e)}))

    else:
        await websocket.send(json.dumps({"error": "Send {type:'hello',agent:'chrome-extension'} or {type:'controller',command:...}"}))


async def cli_repl():
    print(f"\n[bridge] Server on ws://{HOST}:{PORT}")
    print("[bridge] Commands: navigate|click|fill|getText|getLinks|evaluate|snapshot|tabs|quit\n")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        sys.stdout.write("bridge> ")
        sys.stdout.flush()
        line = await reader.readline()
        if not line:
            break
        line = line.decode().strip()
        if not line:
            continue
        if line in ("quit", "exit", "q"):
            break

        parts = line.split(maxsplit=1)
        cmd, rest = parts[0], parts[1] if len(parts) > 1 else ""

        try:
            if cmd == "navigate":
                r = await send_to_extension("navigate", {"url": rest})
            elif cmd == "click":
                r = await send_to_extension("click", {"selector": rest})
            elif cmd == "fill":
                sel, val = rest.split(maxsplit=1)
                r = await send_to_extension("fill", {"selector": sel, "value": val})
            elif cmd == "getText":
                r = await send_to_extension("getText", {"selector": rest} if rest else {})
            elif cmd == "getLinks":
                r = await send_to_extension("getLinks", {"filter": rest} if rest else {})
            elif cmd == "evaluate":
                r = await send_to_extension("evaluate", {"expression": rest})
            elif cmd == "snapshot":
                r = await send_to_extension("snapshot", {})
            elif cmd == "tabs":
                r = await send_to_extension("getTabs", {})
            else:
                print(f"Unknown: {cmd}")
                continue
            print(json.dumps(r, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error: {e}")


async def main():
    async with serve(handle_connection, HOST, PORT):
        print(f"[bridge] Listening on ws://{HOST}:{PORT}")
        if "--no-repl" in sys.argv:
            await asyncio.Future()
        else:
            await cli_repl()


if __name__ == "__main__":
    asyncio.run(main())
