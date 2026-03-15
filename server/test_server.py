#!/usr/bin/env python3
"""
Integration test — simulates Extension ↔ Server communication.
Run without Chrome to verify the WebSocket protocol works.
"""

import asyncio
import json
import pytest

try:
    import websockets
except ImportError:
    pytest.skip("websockets not installed", allow_module_level=True)

from server import main as server_main, send_command, extension_ws

HOST, PORT = "localhost", 9877  # Use different port for tests


async def fake_extension(port: int):
    """Simulates Chrome Extension connecting and responding."""
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        async for message in ws:
            data = json.loads(message)
            cmd = data.get("command")
            msg_id = data.get("id")

            if cmd == "ping":
                await ws.send(json.dumps({"id": msg_id, "ok": True, "result": {"pong": True}}))
            elif cmd == "snapshot":
                await ws.send(json.dumps({
                    "id": msg_id,
                    "ok": True,
                    "result": {
                        "url": "https://example.com",
                        "title": "Example",
                        "text": "Hello World",
                        "links": [],
                        "inputs": [],
                        "buttons": [],
                    },
                }))
            elif cmd == "navigate":
                await ws.send(json.dumps({
                    "id": msg_id,
                    "ok": True,
                    "result": {"url": data["params"]["url"], "loaded": True},
                }))
            else:
                await ws.send(json.dumps({"id": msg_id, "ok": True, "result": {}}))


async def test_protocol():
    """Test the basic request/response protocol."""
    import server as srv
    srv.PORT = PORT

    # Start server
    ws_server = await websockets.serve(srv.handle_extension, HOST, PORT)

    # Start fake extension
    ext_task = asyncio.create_task(fake_extension(PORT))
    await asyncio.sleep(0.2)  # Let it connect

    # Test ping
    result = await send_command("ping")
    assert result["ok"] is True
    assert result["result"]["pong"] is True
    print("✅ ping OK")

    # Test snapshot
    result = await send_command("snapshot")
    assert result["ok"] is True
    assert result["result"]["title"] == "Example"
    print("✅ snapshot OK")

    # Test navigate
    result = await send_command("navigate", {"url": "https://reddit.com"})
    assert result["ok"] is True
    assert result["result"]["url"] == "https://reddit.com"
    print("✅ navigate OK")

    # Cleanup
    ext_task.cancel()
    ws_server.close()
    await ws_server.wait_closed()
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_protocol())
