"""
main.py — FastAPI application entry point for AuraSense.

Run:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Or:
    python -m backend.main
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import SimConfig
from backend.sim_manager import SimManager
from backend.api import routes as rest_routes
from backend.api import websocket as ws_routes


# ─── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-24s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aurasense")


# ─── Lifespan (startup / shutdown) ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the SimManager on startup, clean up on shutdown."""
    cfg = SimConfig()
    mgr = SimManager(cfg)

    # Inject into route modules
    rest_routes.set_manager(mgr)
    ws_routes.set_manager(mgr)

    # Store on app.state for access anywhere
    app.state.manager = mgr

    logger.info("AuraSense backend started  (dt=%.2f min, duration=%.0f min)",
                cfg.dt, cfg.duration)
    yield

    # Shutdown: stop any running simulation
    await mgr.stop()
    logger.info("AuraSense backend shut down")


# ─── App ──────────────────────────────────────────────────
app = FastAPI(
    title="AuraSense — AI Tea Dryer Digital Twin",
    description="Physics engine + sensor simulation + real-time telemetry "
                "for Fluidized Bed Dryer optimization.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend (dev server) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(rest_routes.router)
app.include_router(ws_routes.router)


# ─── Serve React frontend (production build) ─────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    # Serve other static files (vite.svg, etc.)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static-root")

    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for any non-API/WS route (SPA routing)."""
        file = STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")


# ─── Health check ─────────────────────────────────────────
@app.get("/", tags=["health"])
async def root():
    return {
        "app": "AuraSense",
        "version": "0.1.0",
        "docs": "/docs",
    }


# ─── Direct run ──────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
