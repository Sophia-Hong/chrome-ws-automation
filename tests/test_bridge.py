#!/usr/bin/env python3
"""
Tests for the Browser Automation Bridge.
Tests the WebSocket server protocol without needing a real Chrome extension.
"""

import asyncio
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

try:
    import websockets
except ImportError:
    pytest.skip("websockets not installed", allow_module_level=True)


PORT = 19876  # Test port to avoid conflicts


async def start_test_server():
    """Start bridge server on test port."""
    import bridge
    bridge.PORT = PORT
    bridge.HOST = "localhost"
    server = await websockets.serve(bridge.handle_connection, "localhost", PORT)
    return server


async def mock_extension(commands_to_handle=1):
    """Simulate Chrome extension connecting and responding."""
    ws = await websockets.connect(f"ws://localhost:{PORT}")
    await ws.send(json.dumps({"type": "hello", "agent": "chrome-extension"}))

    for _ in range(commands_to_handle):
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        msg = json.loads(raw)
        # Echo back with mock result
        await ws.send(json.dumps({
            "id": msg["id"],
            "result": {"mock": True, "command": msg["command"], "params": msg.get("params", {})},
        }))

    await ws.close()


async def send_controller_command(command, params=None):
    """Send a command as a controller client."""
    ws = await websockets.connect(f"ws://localhost:{PORT}")
    await ws.send(json.dumps({
        "type": "controller",
        "id": "test-1",
        "command": command,
        "params": params or {},
    }))
    raw = await asyncio.wait_for(ws.recv(), timeout=5)
    await ws.close()
    return json.loads(raw)


@pytest.mark.asyncio
async def test_extension_connect_and_command():
    """Test: extension connects, controller sends command, gets response."""
    server = await start_test_server()

    try:
        # Start mock extension in background
        ext_task = asyncio.create_task(mock_extension(1))

        # Give extension time to connect
        await asyncio.sleep(0.2)

        # Send command as controller
        result = await send_controller_command("snapshot")

        assert "result" in result
        assert result["result"]["mock"] is True
        assert result["result"]["command"] == "snapshot"

        await ext_task
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_no_extension_error():
    """Test: controller gets error when no extension is connected."""
    import bridge
    bridge.extension_ws = None

    server = await start_test_server()

    try:
        await asyncio.sleep(0.1)
        result = await send_controller_command("snapshot")
        assert "error" in result
        assert "No Chrome extension" in result["error"]
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_navigate_command():
    """Test navigate command flow."""
    server = await start_test_server()

    try:
        ext_task = asyncio.create_task(mock_extension(1))
        await asyncio.sleep(0.2)

        result = await send_controller_command("navigate", {"url": "https://example.com"})
        assert result["result"]["command"] == "navigate"
        assert result["result"]["params"]["url"] == "https://example.com"

        await ext_task
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
