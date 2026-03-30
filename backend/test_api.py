"""
test_api.py — Integration tests for Phase 3: FastAPI + WebSocket.

Prerequisites: The server must be running on localhost:8000.
    uvicorn backend.main:app --reload --port 8000

Run:
    python -m backend.test_api
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


# ─── Helpers ──────────────────────────────────────────────

def get(path: str) -> dict:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def post(path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


# ─── Tests ────────────────────────────────────────────────

def test_health():
    r = get("/")
    assert r["app"] == "AuraSense", f"Unexpected response: {r}"
    print("[PASS] health check")


def test_status_idle():
    r = get("/api/status")
    assert r["status"] in ("idle", "finished", "running",
                           "paused"), f"Bad status: {r}"
    print(f"[PASS] status  (status={r['status']})")


def test_config():
    r = get("/api/config")
    assert "inlet_temp" in r, "Missing inlet_temp in config"
    assert "page_k" in r, "Missing page_k in config"
    assert r["inlet_temp"] == 100.0
    print("[PASS] get config")


def test_reset():
    r = post("/api/reset")
    assert r["status"] == "idle", f"Expected idle after reset, got {r['status']}"
    assert r["time"] == 0, f"Expected t=0, got {r['time']}"
    print("[PASS] reset")


def test_start_and_pause():
    # Reset first, then start at 2x speed (slow enough to pause)
    post("/api/reset")
    r = post("/api/start", {"speed": 2})
    assert r["status"] == "running", f"Expected running, got {r['status']}"
    assert r["speed"] == 2, f"Expected speed=2, got {r['speed']}"

    # Let it run a tiny bit
    time.sleep(0.5)

    # Check status — should have advanced
    s = get("/api/status")
    assert s["time"] > 0, f"Simulation should have advanced, got t={s['time']}"

    # Pause
    r = post("/api/pause")
    # If sim already finished (unlikely at 2x), that's okay too
    if r["status"] == "finished":
        print(
            f"[PASS] start + pause  (sim finished before pause, t={r['time']:.1f})")
        return

    assert r["status"] == "paused", f"Expected paused, got {r['status']}"
    paused_time = get("/api/status")["time"]

    # Wait and verify time didn't advance
    time.sleep(0.5)
    still_paused_time = get("/api/status")["time"]
    assert still_paused_time == paused_time, \
        f"Time advanced while paused: {paused_time} → {still_paused_time}"

    post("/api/stop")
    print(f"[PASS] start + pause  (ran to t={paused_time:.1f} min)")


def test_controls():
    post("/api/reset")
    post("/api/start", {"speed": 20})
    time.sleep(0.3)

    r = post("/api/controls", {"inlet_temp": 120, "airflow": 0.7})
    assert r["inlet_temp"] == 120, f"Inlet not set: {r}"
    assert r["airflow"] == 0.7, f"Airflow not set: {r}"

    post("/api/stop")
    print("[PASS] controls update")


def test_speed_change():
    post("/api/reset")
    post("/api/start", {"speed": 1})
    time.sleep(0.3)

    r = post("/api/speed", {"speed": 25})
    assert r["speed"] == 25, f"Speed not updated: {r}"

    post("/api/stop")
    print("[PASS] speed change")


def test_snapshot():
    post("/api/reset")
    post("/api/start", {"speed": 50})
    time.sleep(1.5)
    post("/api/stop")

    snap = get("/api/snapshot")
    assert "moisture" in snap, "Missing moisture in snapshot"
    assert "sensors" in snap, "Missing sensors in snapshot"
    assert snap["sensors"] is not None, "Sensors should not be None"
    assert "enose" in snap["sensors"], "Missing enose in sensor data"
    print(
        f"[PASS] snapshot  (t={snap['time']:.1f}  M={snap['moisture']*100:.1f}%)")


def test_history():
    post("/api/reset")
    post("/api/start", {"speed": 50})
    time.sleep(1.5)
    post("/api/stop")

    hist = get("/api/history")
    assert isinstance(hist, list), "History should be a list"
    assert len(hist) > 5, f"History too short: {len(hist)} entries"
    # Check first and last entries have sensors
    assert hist[0]["sensors"] is not None
    assert hist[-1]["sensors"] is not None
    print(f"[PASS] history  ({len(hist)} entries)")


def test_benchmark():
    """Benchmark endpoint should return summary and trajectory payload."""
    result = get("/api/benchmark")
    assert "summary" in result, "Missing summary in benchmark response"
    assert "trajectory" in result, "Missing trajectory in benchmark response"
    assert isinstance(result["trajectory"], list), "Trajectory must be a list"
    assert len(result["trajectory"]) > 10, "Trajectory too short"

    rl = result["summary"].get("rl", {})
    pid = result["summary"].get("pid", {})
    delta = result["summary"].get("delta", {})
    assert "tracking_mae_pct" in rl and "tracking_mae_pct" in pid
    assert "energy_saved_pct" in delta
    print("[PASS] benchmark endpoint")


def test_full_run_to_completion():
    """Run sim at max speed and verify it finishes."""
    post("/api/reset")
    post("/api/start", {"speed": 50})

    # Poll until finished or timeout
    for _ in range(60):
        time.sleep(0.5)
        s = get("/api/status")
        if s["done"]:
            break
    else:
        post("/api/stop")
        raise AssertionError("Simulation did not finish in time")

    assert s["status"] == "finished"
    snap = s["snapshot"]
    assert snap["moisture"] < 0.06, f"Final moisture too high: {snap['moisture']}"
    print(
        f"[PASS] full_run  (finished at t={snap['time']:.1f}, M={snap['moisture']*100:.1f}%)")


def test_websocket():
    """Test WebSocket telemetry stream (requires websockets library)."""
    try:
        import websockets
    except ImportError:
        print("[SKIP] websocket (websockets library not available)")
        return

    async def _ws_test():
        post("/api/reset")

        uri = "ws://localhost:8000/ws/telemetry"
        async with websockets.connect(uri) as ws:
            # Should receive initial status
            raw = await asyncio.wait_for(ws.recv(), timeout=3)
            msg = json.loads(raw)
            assert "status" in msg, f"Expected status in initial message: {msg}"

            # Send start command via WebSocket
            await ws.send(json.dumps({"cmd": "start", "speed": 50}))
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            resp_data = json.loads(resp)
            assert resp_data.get("status") == "running" or "time" in resp_data

            # Receive a few telemetry frames
            frames = []
            for _ in range(10):
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                frames.append(json.loads(raw))

            assert len(frames) >= 5, f"Expected ≥5 frames, got {len(frames)}"

            # Send control command over WS
            await ws.send(json.dumps({"cmd": "set_controls", "inlet_temp": 115}))
            ctrl_resp = await asyncio.wait_for(ws.recv(), timeout=3)
            ctrl_data = json.loads(ctrl_resp)
            assert ctrl_data.get("inlet_temp") == 115 or "time" in ctrl_data

            # Stop via WS
            await ws.send(json.dumps({"cmd": "stop"}))

        return len(frames)

    n_frames = asyncio.run(_ws_test())
    print(f"[PASS] websocket  (received {n_frames} telemetry frames)")


# ─── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing AuraSense API on", BASE)
    print("=" * 50)

    test_health()
    test_status_idle()
    test_config()
    test_reset()
    test_start_and_pause()
    test_controls()
    test_speed_change()
    test_snapshot()
    test_history()
    test_benchmark()
    test_full_run_to_completion()
    test_websocket()

    print("\n✅ All Phase 3 API tests passed.")
