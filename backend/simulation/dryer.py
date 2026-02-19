"""
dryer.py — Unified Fluidized Bed Dryer state machine.

This module ties together moisture, enzyme, flavor, and color sub-models
into one coherent, time-stepped simulation.  It is the single entry point
that the rest of the system (RL env, API, UI) will call.

Key responsibilities
--------------------
1. Maintain the full state vector at every tick.
2. Compute bed temperature from inlet temperature via a first-order thermal
   lag (τ = BED_TEMP_LAG_TAU).  This models the real-world delay between
   burner adjustment and the tea actually feeling the heat.
3. Step every sub-model forward by dt and record history.
4. Expose a `snapshot()` dict for easy JSON serialisation to the frontend.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Any

from backend.config import SimConfig
from backend.simulation.moisture import moisture_content, _effective_k, moisture_ratio
from backend.simulation.enzyme import step_enzyme, StewingTracker
from backend.simulation.flavor import step_flavor
from backend.simulation.color import lab, lab_to_hex, lab_to_rgb
from backend.simulation.sensors import SensorSuite, SensorReading


@dataclass
class DryerState:
    """Instantaneous snapshot of every simulated quantity."""
    time: float           # elapsed minutes
    moisture: float       # wet-basis fraction
    bed_temp: float       # °C
    inlet_temp: float     # °C  (control input)
    airflow: float        # 0–1 damper position (control input)
    enzyme_activity: float  # normalised [0, 1]
    pyrazine: float       # µg / g dry matter
    l_star: float         # CIELAB L*
    a_star: float         # CIELAB a*
    b_star: float         # CIELAB b*
    color_hex: str        # e.g. "#8b5e3c"
    stewing: bool         # currently in stewing zone?
    stewing_penalty: bool  # stewing time limit exceeded?
    drying_rate: float    # dM/dt  (fraction/min, negative)
    sensors: SensorReading | None = None   # Phase 2: synthetic sensor readings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time":             round(self.time, 3),
            "moisture":         round(self.moisture, 5),
            "bed_temp":         round(self.bed_temp, 2),
            "inlet_temp":       round(self.inlet_temp, 2),
            "airflow":          round(self.airflow, 3),
            "enzyme_activity":  round(self.enzyme_activity, 5),
            "pyrazine":         round(self.pyrazine, 4),
            "l_star":           round(self.l_star, 2),
            "a_star":           round(self.a_star, 2),
            "b_star":           round(self.b_star, 2),
            "color_hex":        self.color_hex,
            "stewing":          self.stewing,
            "stewing_penalty":  self.stewing_penalty,
            "drying_rate":      round(self.drying_rate, 6),
            "sensors":          self.sensors.to_dict() if self.sensors else None,
        }


class FBDSimulation:
    """
    Fluidized Bed Dryer simulation driver.

    Usage
    -----
        sim = FBDSimulation()           # uses defaults
        sim = FBDSimulation(cfg)        # custom config

        # Run the full drying cycle
        history = sim.run()

        # — or — step interactively (for RL / live UI)
        while not sim.done:
            sim.set_controls(inlet_temp=105, airflow=0.8)
            state = sim.step()
    """

    def __init__(self, cfg: SimConfig | None = None) -> None:
        self.cfg = cfg or SimConfig()
        self._reset()

    # ─── lifecycle ────────────────────────────────────────
    def _reset(self) -> None:
        c = self.cfg
        self.t: float = 0.0
        self.moisture: float = c.m0
        self.bed_temp: float = c.ambient_temp   # starts cold
        self.inlet_temp: float = c.inlet_temp
        self.airflow: float = c.airflow
        self.enzyme: float = c.c0_enzyme
        self.pyrazine: float = 0.0
        self.stew_tracker = StewingTracker(c)
        self.sensor_suite = SensorSuite(c)
        self.history: List[DryerState] = []
        self.done: bool = False

        # record initial state
        self.history.append(self._snapshot())

    def reset(self) -> DryerState:
        """Reset simulation to t = 0 and return initial state."""
        self._reset()
        self.sensor_suite.reset()
        return self.history[0]

    # ─── control interface ────────────────────────────────
    def set_controls(self, inlet_temp: float | None = None,
                     airflow: float | None = None) -> None:
        """Update the two control knobs (call before `step`)."""
        if inlet_temp is not None:
            self.inlet_temp = max(50.0, min(150.0, inlet_temp))  # safety clamp
        if airflow is not None:
            self.airflow = max(0.0, min(1.0, airflow))

    # ─── single time-step ─────────────────────────────────
    def step(self, dt: float | None = None) -> DryerState:
        """
        Advance the simulation by `dt` minutes (default: cfg.dt).
        Returns the new DryerState.
        """
        if self.done:
            return self.history[-1]

        dt = dt or self.cfg.dt
        self.t += dt

        # 1. Bed temperature — first-order lag toward inlet temp
        #    dT_bed/dt = (T_inlet - T_bed) / τ
        tau = self.cfg.bed_temp_lag_tau
        self.bed_temp += ((self.inlet_temp - self.bed_temp) / tau) * dt

        # 2. Moisture — Page model (uses effective elapsed time)
        k_eff = _effective_k(self.cfg.page_k, self.inlet_temp, self.airflow)
        mr = moisture_ratio(self.t, k_eff, self.cfg.page_n)
        new_moisture = self.cfg.me + (self.cfg.m0 - self.cfg.me) * mr
        drying_rate = (new_moisture - self.moisture) / dt
        self.moisture = new_moisture

        # 3. Enzyme denaturation
        self.enzyme = step_enzyme(self.enzyme, self.bed_temp, dt, self.cfg)

        # 4. Stewing check
        self.stew_tracker.update(self.bed_temp, self.moisture, dt)

        # 5. Maillard / pyrazine
        self.pyrazine = step_flavor(
            self.pyrazine, self.bed_temp, self.moisture, dt, self.cfg
        )

        # 6. Color
        L, a, b = lab(self.t, self.bed_temp, self.cfg)

        # 7. Termination check
        if self.t >= self.cfg.duration or self.moisture <= self.cfg.me + 0.005:
            self.done = True

        snap = self._snapshot(drying_rate=drying_rate, L=L, a=a, b=b, dt=dt)
        self.history.append(snap)
        return snap

    # ─── batch run ────────────────────────────────────────
    def run(self) -> List[DryerState]:
        """Run the entire drying cycle with fixed controls. Returns history."""
        while not self.done:
            self.step()
        return self.history

    # ─── snapshot builder ─────────────────────────────────
    def _snapshot(self, drying_rate: float = 0.0,
                  L: float | None = None,
                  a: float | None = None,
                  b: float | None = None,
                  dt: float | None = None) -> DryerState:
        if L is None or a is None or b is None:
            L, a, b = lab(self.t, self.bed_temp, self.cfg)
        hex_col = lab_to_hex(L, a, b)

        # Sensor reading
        sensor_rd = self.sensor_suite.read(
            time=self.t,
            moisture=self.moisture,
            enzyme_activity=self.enzyme,
            pyrazine=self.pyrazine,
            bed_temp=self.bed_temp,
            inlet_temp=self.inlet_temp,
            drying_rate=drying_rate,
            l_star=L,
            a_star=a,
            b_star=b,
            dt=dt or self.cfg.dt,
        )

        return DryerState(
            time=self.t,
            moisture=self.moisture,
            bed_temp=self.bed_temp,
            inlet_temp=self.inlet_temp,
            airflow=self.airflow,
            enzyme_activity=self.enzyme,
            pyrazine=self.pyrazine,
            l_star=L,
            a_star=a,
            b_star=b,
            color_hex=hex_col,
            stewing=self.stew_tracker.is_stewing,
            stewing_penalty=self.stew_tracker.penalty_triggered,
            drying_rate=drying_rate,
            sensors=sensor_rd,
        )

    # ─── convenience ──────────────────────────────────────
    def snapshot_dict(self) -> Dict[str, Any]:
        """Current state as a JSON-ready dict."""
        return self.history[-1].to_dict() if self.history else {}

    def history_dicts(self) -> List[Dict[str, Any]]:
        """Full history as a list of JSON-ready dicts."""
        return [s.to_dict() for s in self.history]
