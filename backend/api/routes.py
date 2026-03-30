"""
routes.py — REST API endpoints for the AuraSense simulation.

Endpoints
---------
POST  /api/start          Start or resume the simulation
POST  /api/pause          Pause the simulation
POST  /api/stop           Stop the simulation
POST  /api/reset          Reset to t=0 (optionally with new config)
GET   /api/status         Current simulation status + latest state
GET   /api/snapshot       Latest physics state
GET   /api/history        Full simulation history (can be large)
POST  /api/controls       Update inlet_temp / airflow
POST  /api/speed          Change simulation speed multiplier
GET   /api/config         Get current configuration
POST  /api/config         Update configuration (requires reset)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import SimConfig
from backend.rl.benchmark import run_benchmark

router = APIRouter(prefix="/api", tags=["simulation"])

# ─── We'll inject the SimManager at app startup ──────────
# This gets set by main.py when the app boots
_manager = None


def set_manager(mgr):
    """Called by main.py to inject the SimManager instance."""
    global _manager
    _manager = mgr


def _mgr():
    if _manager is None:
        raise HTTPException(
            status_code=503, detail="Simulation manager not initialised")
    return _manager


# ─── Request / Response models ────────────────────────────

class StartRequest(BaseModel):
    speed: Optional[float] = Field(
        None, ge=0.1, le=50.0, description="Simulation speed multiplier")


class ControlsRequest(BaseModel):
    inlet_temp: Optional[float] = Field(
        None, ge=50.0, le=150.0, description="Inlet temperature °C")
    airflow: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Airflow damper position 0–1")


class SpeedRequest(BaseModel):
    speed: float = Field(..., ge=0.1, le=50.0,
                         description="Simulation speed multiplier")


class ConfigRequest(BaseModel):
    """Subset of SimConfig fields that can be changed at runtime (requires reset)."""
    inlet_temp: Optional[float] = Field(None, ge=50.0, le=150.0)
    airflow: Optional[float] = Field(None, ge=0.0, le=1.0)
    duration: Optional[float] = Field(None, ge=5.0, le=120.0)
    page_k: Optional[float] = Field(None, ge=0.01, le=1.0)
    page_n: Optional[float] = Field(None, ge=0.5, le=2.0)
    dt: Optional[float] = Field(None, ge=0.01, le=1.0)


# ─── Endpoints ────────────────────────────────────────────

@router.post("/start")
async def start_simulation(req: StartRequest = StartRequest()):
    """Start or resume the simulation."""
    result = await _mgr().start(speed=req.speed)
    return result


@router.post("/pause")
async def pause_simulation():
    """Pause the running simulation."""
    return await _mgr().pause()


@router.post("/stop")
async def stop_simulation():
    """Stop the simulation entirely."""
    return await _mgr().stop()


@router.post("/reset")
async def reset_simulation(req: ConfigRequest = ConfigRequest()):
    """Reset simulation to t=0. Optionally update config parameters."""
    mgr = _mgr()
    # Build new config by overlaying provided fields onto current config
    current = mgr.cfg
    overrides = req.model_dump(exclude_none=True)
    if overrides:
        cfg_dict = {
            f.name: getattr(current, f.name)
            for f in current.__dataclass_fields__.values()
        }
        cfg_dict.update(overrides)
        new_cfg = SimConfig(**cfg_dict)
    else:
        new_cfg = current
    return await mgr.reset(cfg=new_cfg)


@router.get("/status")
async def get_status():
    """Get current simulation status and latest state."""
    return _mgr().get_status()


@router.get("/snapshot")
async def get_snapshot():
    """Get the latest physics state snapshot."""
    return _mgr().get_snapshot()


@router.get("/history")
async def get_history():
    """Get the full simulation history (array of state dicts)."""
    return _mgr().get_history()


@router.get("/benchmark")
async def get_benchmark(model: str | None = Query(None, description="Optional PPO model name under models/")):
    """Run an offline RL-vs-PID benchmark using current simulation config."""
    mgr = _mgr()
    return run_benchmark(sim_cfg=mgr.cfg, model_name=model)


@router.post("/controls")
async def update_controls(req: ControlsRequest):
    """Update inlet temperature and/or airflow while the simulation is running."""
    return await _mgr().set_controls(
        inlet_temp=req.inlet_temp,
        airflow=req.airflow,
    )


@router.post("/speed")
async def update_speed(req: SpeedRequest):
    """Change simulation speed multiplier (1× = real-time, 50× = fast-forward)."""
    return await _mgr().set_speed(req.speed)


@router.get("/config")
async def get_config():
    """Get the current simulation configuration."""
    mgr = _mgr()
    cfg = mgr.cfg
    return {
        f.name: getattr(cfg, f.name)
        for f in cfg.__dataclass_fields__.values()
    }


@router.post("/config")
async def update_config(req: ConfigRequest):
    """
    Update configuration and reset the simulation.
    Only non-None fields are changed; everything else keeps its current value.
    """
    return await reset_simulation(req)
