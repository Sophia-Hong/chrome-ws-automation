#!/usr/bin/env python3
"""
WebSocket server for Chrome browser automation.
Listens on ws://localhost:9876, accepts Chrome Extension connection,
and provides a command interface for automation.
"""

import asyncio
import json
import uuid
import sys
from typing import Optional

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

HOST = "localhost"
PORT = 9876

# Global state
extension_ws = None
pending: dict[str, asyncio.Future] = {}


async def handle_extension(websocket):
    """Handle the Chrome Extension WebSocket connection."""
    global extension_ws
    extension_ws = websocket
    print(f"[server] Extension connected from {websocket.remote_address}")

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_id = data.get("id")
            if msg_id and msg_id in pending:
                pending[msg_id].set_result(data)
    except websockets.ConnectionClosed:
        print("[server] Extension disconnected")
    finally:
        extension_ws = None


async def send_command(command: str, params: Optional[dict] = None, timeout: float = 30.0) -> dict:
    """Send a command to the Chrome Extension and wait for response."""
    if not extension_ws:
        raise RuntimeError("No extension connected")

    msg_id = str(uuid.uuid4())[:8]
    future = asyncio.get_event_loop().create_future()
    pending[msg_id] = future

    await extension_ws.send(json.dumps({
        "id": msg_id,
        "command": command,
        "params": params or {},
    }))

    try:
        result = await asyncio.wait_for(future, timeout=timeout)
        return result
    except asyncio.TimeoutError:
        raise TimeoutError(f"Command '{command}' timed out after {timeout}s")
    finally:
        pending.pop(msg_id, None)


# ── High-level API ──

async def navigate(url: str) -> dict:
    return await send_command("navigate", {"url": url})

async def click(selector: str = None, text: str = None) -> dict:
    params = {}
    if selector: params["selector"] = selector
    if text: params["text"] = text
    return await send_command("click", params)

async def fill(selector: str, value: str) -> dict:
    return await send_command("fill", {"selector": selector, "value": value})

async def evaluate(expression: str) -> dict:
    return await send_command("evaluate", {"expression": expression})

async def snapshot() -> dict:
    return await send_command("snapshot")

async def get_text(selector: str = None) -> dict:
    return await send_command("getText", {"selector": selector} if selector else {})

async def get_links() -> dict:
    return await send_command("getLinks")

async def get_title() -> dict:
    return await send_command("getTitle")

async def get_tabs() -> dict:
    return await send_command("getTabs")

async def ping() -> dict:
    return await send_command("ping")


# ── Interactive CLI ──

async def cli_loop():
    """Interactive CLI for sending commands."""
    print("\n[cli] Commands: navigate <url> | click <selector> | fill <selector> <value>")
    print("[cli]           evaluate <expr> | snapshot | getText [selector] | getLinks")
    print("[cli]           getTabs | getTitle | ping | quit\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, lambda: input(">>> "))
        except (EOFError, KeyboardInterrupt):
            break

        line = line.strip()
        if not line:
            continue
        if line in ("quit", "exit", "q"):
            break

        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        try:
            if cmd == "navigate":
                r = await navigate(arg)
            elif cmd == "click":
                r = await click(selector=arg if arg else None)
            elif cmd == "fill":
                sp = arg.split(maxsplit=1)
                r = await fill(sp[0], sp[1] if len(sp) > 1 else "")
            elif cmd == "evaluate":
                r = await evaluate(arg)
            elif cmd == "snapshot":
                r = await snapshot()
            elif cmd == "getText":
                r = await get_text(arg if arg else None)
            elif cmd == "getLinks":
                r = await get_links()
            elif cmd == "getTabs":
                r = await get_tabs()
            elif cmd == "getTitle":
                r = await get_title()
            elif cmd == "ping":
                r = await ping()
            else:
                print(f"Unknown command: {cmd}")
                continue

            print(json.dumps(r, indent=2, ensure_ascii=False)[:5000])
        except Exception as e:
            print(f"Error: {e}")


async def main():
    print(f"[server] Starting on ws://{HOST}:{PORT}")
    server = await websockets.serve(handle_extension, HOST, PORT)
    print(f"[server] Waiting for Chrome Extension to connect...")

    if "--cli" in sys.argv:
        await cli_loop()
        server.close()
    else:
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
