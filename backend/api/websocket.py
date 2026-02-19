"""
websocket.py — WebSocket telemetry handler for real-time streaming.

Endpoint:  ws://host:8000/ws/telemetry

Protocol
--------
After connection, the server immediately sends the current state.
Then it streams JSON frames at ~10 Hz (at 1× speed) as the simulation runs.

The client can also send JSON commands over the same socket:
    {"cmd": "set_controls", "inlet_temp": 110, "airflow": 0.8}
    {"cmd": "set_speed", "speed": 5}
    {"cmd": "start"}
    {"cmd": "pause"}
    {"cmd": "stop"}
    {"cmd": "reset"}

This allows a fully bidirectional control + telemetry channel — the frontend
doesn't need separate REST calls for basic control while watching the stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("aurasense.ws")

# Injected by main.py
_manager = None


def set_manager(mgr):
    global _manager
    _manager = mgr


@router.websocket("/ws/telemetry")
async def telemetry_endpoint(ws: WebSocket):
    """
    Full-duplex WebSocket:
      ← Server pushes telemetry frames (JSON)
      → Client sends control commands (JSON)
    """
    if _manager is None:
        await ws.close(code=1013, reason="Simulation manager not ready")
        return

    await ws.accept()
    mgr = _manager
    queue = mgr.subscribe()
    logger.info("WebSocket client connected  (subscribers=%d)",
                len(mgr._subscribers))

    # Send current state immediately so the UI can render before sim starts
    try:
        await ws.send_json(mgr.get_status())
    except Exception:
        mgr.unsubscribe(queue)
        return

    # Two concurrent tasks: send telemetry + receive commands
    send_task = asyncio.create_task(_send_loop(ws, queue))
    recv_task = asyncio.create_task(_recv_loop(ws, mgr))

    try:
        # Wait for either task to finish (disconnect or error)
        done, pending = await asyncio.wait(
            {send_task, recv_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception:
        pass
    finally:
        mgr.unsubscribe(queue)
        logger.info("WebSocket client disconnected  (subscribers=%d)",
                    len(mgr._subscribers))


async def _send_loop(ws: WebSocket, queue: asyncio.Queue):
    """Drain the subscription queue and push frames to the client."""
    try:
        while True:
            frame = await queue.get()
            await ws.send_json(frame)
    except (WebSocketDisconnect, Exception):
        return


async def _recv_loop(ws: WebSocket, mgr):
    """Listen for control commands from the client."""
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "invalid JSON"})
                continue

            resp = await _handle_command(msg, mgr)
            await ws.send_json(resp)

    except (WebSocketDisconnect, Exception):
        return


async def _handle_command(msg: Dict[str, Any], mgr) -> Dict[str, Any]:
    """Dispatch a client command and return a response dict."""
    cmd = msg.get("cmd", "").lower()

    if cmd == "start":
        speed = msg.get("speed")
        return await mgr.start(speed=speed)

    elif cmd == "pause":
        return await mgr.pause()

    elif cmd == "stop":
        return await mgr.stop()

    elif cmd == "reset":
        return await mgr.reset()

    elif cmd == "set_controls":
        return await mgr.set_controls(
            inlet_temp=msg.get("inlet_temp"),
            airflow=msg.get("airflow"),
        )

    elif cmd == "set_speed":
        speed = msg.get("speed", 1.0)
        return await mgr.set_speed(speed)

    elif cmd == "status":
        return mgr.get_status()

    else:
        return {"error": f"unknown command: {cmd}"}
