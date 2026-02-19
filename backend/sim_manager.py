"""
sim_manager.py — Async simulation lifecycle manager.

Bridges the synchronous physics engine (FBDSimulation) with the async
FastAPI / WebSocket world.  Manages:

    • Starting / stopping / resetting the simulation loop
    • Configurable simulation speed (1×–50× real-time)
    • Broadcasting state snapshots to all connected WebSocket clients
    • Thread-safe control updates from REST endpoints

The simulation loop runs as an asyncio.Task, ticking the physics engine at
the configured rate and pushing each frame into an asyncio.Queue that the
WebSocket handler drains.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from backend.config import SimConfig
from backend.simulation.dryer import FBDSimulation, DryerState


class SimStatus(str, Enum):
    IDLE = "idle"        # created but never started
    RUNNING = "running"     # actively ticking
    PAUSED = "paused"      # paused mid-run
    FINISHED = "finished"    # drying cycle complete


class SimManager:
    """
    Singleton-style manager for the simulation lifecycle.

    Usage (inside FastAPI lifespan or routes):
        mgr = SimManager()
        await mgr.start()
        ...
        await mgr.stop()
    """

    def __init__(self, cfg: SimConfig | None = None) -> None:
        self.cfg = cfg or SimConfig()
        self.sim = FBDSimulation(self.cfg)
        self.status: SimStatus = SimStatus.IDLE
        self.speed: float = 1.0            # simulation speed multiplier
        self._task: Optional[asyncio.Task] = None
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    # ─── subscriber management ────────────────────────────
    def subscribe(self) -> asyncio.Queue:
        """Create a new queue for a WebSocket client. Returns the queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=120)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a client queue."""
        self._subscribers.discard(q)

    async def _broadcast(self, frame: Dict[str, Any]) -> None:
        """Push a frame to every subscriber queue (non-blocking)."""
        dead: List[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(frame)
            except asyncio.QueueFull:
                # Drop oldest frame to keep stream live
                try:
                    q.get_nowait()
                    q.put_nowait(frame)
                except Exception:
                    dead.append(q)
        for q in dead:
            self._subscribers.discard(q)

    # ─── lifecycle ────────────────────────────────────────
    async def start(self, speed: float | None = None) -> Dict[str, Any]:
        """Start or resume the simulation loop."""
        async with self._lock:
            if speed is not None:
                self.speed = max(0.1, min(50.0, speed))

            if self.status == SimStatus.RUNNING:
                return self._status_dict("already running")

            if self.status in (SimStatus.IDLE, SimStatus.FINISHED):
                # Fresh start
                self.sim = FBDSimulation(self.cfg)
                self.status = SimStatus.RUNNING
            elif self.status == SimStatus.PAUSED:
                self.status = SimStatus.RUNNING

            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._loop())

            return self._status_dict("started")

    async def pause(self) -> Dict[str, Any]:
        """Pause the simulation (can be resumed)."""
        async with self._lock:
            if self.status == SimStatus.RUNNING:
                self.status = SimStatus.PAUSED
                return self._status_dict("paused")
            return self._status_dict("not running")

    async def stop(self) -> Dict[str, Any]:
        """Stop the simulation entirely."""
        async with self._lock:
            self.status = SimStatus.IDLE
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None
            return self._status_dict("stopped")

    async def reset(self, cfg: SimConfig | None = None) -> Dict[str, Any]:
        """Stop + reset to t=0 with optional new config."""
        await self.stop()
        async with self._lock:
            if cfg is not None:
                self.cfg = cfg
            self.sim = FBDSimulation(self.cfg)
            self.status = SimStatus.IDLE
            return self._status_dict("reset")

    # ─── control updates ──────────────────────────────────
    async def set_controls(self, inlet_temp: float | None = None,
                           airflow: float | None = None) -> Dict[str, Any]:
        """Update dryer control knobs (safe to call while running)."""
        self.sim.set_controls(inlet_temp=inlet_temp, airflow=airflow)
        return {
            "inlet_temp": self.sim.inlet_temp,
            "airflow": self.sim.airflow,
        }

    async def set_speed(self, speed: float) -> Dict[str, Any]:
        """Change simulation speed multiplier."""
        self.speed = max(0.1, min(50.0, speed))
        return {"speed": self.speed}

    # ─── the simulation loop ──────────────────────────────
    async def _loop(self) -> None:
        """
        Async loop that ticks the physics engine and broadcasts frames.

        Timing: at 1× speed, one physics tick (dt = 0.1 min = 6 seconds
        of sim time) should take ~100ms of wall time to give the frontend
        a smooth 10 Hz update.  At higher speeds, ticks come faster.
        """
        # Target wall-clock interval per tick at 1× speed
        base_interval = 0.1  # seconds (→ 10 Hz)

        while self.status == SimStatus.RUNNING and not self.sim.done:
            t_start = asyncio.get_event_loop().time()

            # Tick the physics engine
            state = self.sim.step()
            frame = state.to_dict()
            frame["sim_status"] = self.status.value
            frame["speed"] = self.speed

            # Broadcast to all WebSocket subscribers
            await self._broadcast(frame)

            # Check if simulation is finished
            if self.sim.done:
                self.status = SimStatus.FINISHED
                # Send final status frame
                frame["sim_status"] = self.status.value
                await self._broadcast(frame)
                break

            # Sleep to maintain target tick rate
            elapsed = asyncio.get_event_loop().time() - t_start
            target = base_interval / self.speed
            sleep_time = max(0, target - elapsed)
            await asyncio.sleep(sleep_time)

    # ─── status / snapshot ────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        """Current simulation status + latest state."""
        return self._status_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        """Latest physics state as a dict."""
        return self.sim.snapshot_dict()

    def get_history(self) -> List[Dict[str, Any]]:
        """Full simulation history."""
        return self.sim.history_dicts()

    def _status_dict(self, message: str = "") -> Dict[str, Any]:
        snap = self.sim.snapshot_dict()
        return {
            "status": self.status.value,
            "message": message,
            "speed": self.speed,
            "time": snap.get("time", 0),
            "done": self.sim.done,
            "subscribers": len(self._subscribers),
            "snapshot": snap,
        }
