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
from typing import Dict, List, Any, Optional

from backend.config import SimConfig
from backend.simulation.moisture import moisture_content, _effective_k, moisture_ratio
from backend.simulation.enzyme import step_enzyme, StewingTracker
from backend.simulation.flavor import step_flavor
from backend.simulation.color import lab, lab_to_hex, lab_to_rgb
from backend.simulation.sensors import SensorSuite, SensorReading


# ─── Co-Pilot Alert ─────────────────────────────────────
@dataclass
class CoPilotAlert:
    """A single advisory alert from the AI Co-Pilot."""
    time: float           # sim-time in minutes
    severity: str         # "warning" | "success" | "danger" | "info"
    tag: str              # short machine-readable tag for dedup
    title: str            # one-line heading
    detail: str           # longer description / recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": round(self.time, 2),
            "severity": self.severity,
            "tag": self.tag,
            "title": self.title,
            "detail": self.detail,
        }


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
    # Energy & cost fields
    power_kw: float = 0.0             # instantaneous heater + fan draw
    energy_kwh: float = 0.0           # cumulative energy consumed
    operating_cost_inr: float = 0.0   # cumulative cost in ₹
    # specific energy consumption (kWh per kg water removed)
    sec: float = 0.0
    water_removed_kg: float = 0.0     # cumulative water evaporated
    batch_value_inr: float = 0.0      # estimated value of finished dry tea
    sensors: SensorReading | None = None   # Phase 2: synthetic sensor readings
    alerts: List[CoPilotAlert] = field(
        default_factory=list)  # new alerts this tick

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
            "power_kw":         round(self.power_kw, 3),
            "energy_kwh":       round(self.energy_kwh, 4),
            "operating_cost_inr": round(self.operating_cost_inr, 2),
            "sec":              round(self.sec, 3),
            "water_removed_kg": round(self.water_removed_kg, 3),
            "batch_value_inr":  round(self.batch_value_inr, 2),
            "sensors":          self.sensors.to_dict() if self.sensors else None,
            "alerts":           [a.to_dict() for a in self.alerts],
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

        # Energy tracking
        self._energy_kwh: float = 0.0
        self._water_removed_kg: float = 0.0

        # Co-Pilot alert state
        self._low_temp_accum: float = 0.0       # minutes bed < 70 °C
        # tag -> last fire time (cooldown)
        self._last_alert_tags: Dict[str, float] = {}
        self._target_alerted: bool = False
        self._efficiency_warned: bool = False

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
        c = self.cfg

        # 1. Bed temperature — first-order lag toward inlet temp
        #    dT_bed/dt = (T_inlet - T_bed) / τ
        tau = c.bed_temp_lag_tau
        self.bed_temp += ((self.inlet_temp - self.bed_temp) / tau) * dt

        # 2. Moisture — Page model (uses effective elapsed time)
        k_eff = _effective_k(c.page_k, self.inlet_temp, self.airflow)
        mr = moisture_ratio(self.t, k_eff, c.page_n)
        new_moisture = c.me + (c.m0 - c.me) * mr
        drying_rate = (new_moisture - self.moisture) / dt
        old_moisture = self.moisture
        self.moisture = new_moisture

        # 3. Enzyme denaturation
        self.enzyme = step_enzyme(self.enzyme, self.bed_temp, dt, c)

        # 4. Stewing check
        self.stew_tracker.update(self.bed_temp, self.moisture, dt)

        # 5. Maillard / pyrazine
        self.pyrazine = step_flavor(
            self.pyrazine, self.bed_temp, self.moisture, dt, c
        )

        # 6. Color
        L, a, b = lab(self.t, self.bed_temp, c)

        # ── 7. Energy & Cost ──────────────────────────────
        heater_kw = c.base_heater_kw * \
            (self.inlet_temp / 100.0) ** 1.3 * max(self.airflow, 0.05)
        fan_kw = c.fan_power_kw * max(self.airflow, 0.05) ** 0.8
        power_kw = heater_kw + fan_kw
        dt_hours = dt / 60.0
        self._energy_kwh += power_kw * dt_hours
        operating_cost = self._energy_kwh * c.electricity_rate

        # Water removed (kg): batch_size × ΔM  (wet-basis simplification)
        delta_water = max(0.0, old_moisture - new_moisture) * c.batch_size_kg
        self._water_removed_kg += delta_water

        # SEC = kWh / kg water evaporated (avoid div-by-zero)
        sec = self._energy_kwh / self._water_removed_kg if self._water_removed_kg > 0.01 else 0.0

        # Estimated dry-tea output value
        #   dry_mass ≈ batch_size × (1 - M0) (the solids are constant)
        dry_mass_kg = c.batch_size_kg * (1.0 - c.m0)
        batch_value = dry_mass_kg * c.tea_value_per_kg

        # ── 8. Co-Pilot Alerts ─────────────────────────────
        alerts = self._generate_alerts(dt, drying_rate, sec)

        # ── 9. Termination check ───────────────────────────
        if self.t >= c.duration or self.moisture <= c.me + 0.005:
            self.done = True

        snap = self._snapshot(
            drying_rate=drying_rate, L=L, a=a, b=b, dt=dt,
            power_kw=power_kw, energy_kwh=self._energy_kwh,
            operating_cost_inr=operating_cost, sec=sec,
            water_removed_kg=self._water_removed_kg,
            batch_value_inr=batch_value, alerts=alerts,
        )
        self.history.append(snap)
        return snap

    # ─── Co-Pilot Alert Engine ────────────────────────────
    def _can_fire(self, tag: str, cooldown: float = 2.0) -> bool:
        """Rate-limit alerts: same tag can only fire once per `cooldown` minutes."""
        last = self._last_alert_tags.get(tag, -999)
        if self.t - last >= cooldown:
            self._last_alert_tags[tag] = self.t
            return True
        return False

    def _generate_alerts(self, dt: float, drying_rate: float, sec: float) -> List[CoPilotAlert]:
        alerts: List[CoPilotAlert] = []

        # ① Case-hardening risk (bed_temp > 105 °C)
        if self.bed_temp > 105 and self._can_fire("case_hard", 3.0):
            alerts.append(CoPilotAlert(
                time=self.t, severity="warning", tag="case_hard",
                title="Case-Hardening Risk",
                detail=f"Bed temp {self.bed_temp:.1f}°C exceeds 105°C. "
                "Enzyme degradation accelerating. Recommend reducing Inlet Temp.",
            ))

        # ② Target moisture approaching
        if self.moisture * 100 < 5.0 and drying_rate < -0.001 and not self._target_alerted:
            self._target_alerted = True
            alerts.append(CoPilotAlert(
                time=self.t, severity="success", tag="target_near",
                title="Target Moisture Approaching",
                detail=f"Moisture at {self.moisture*100:.1f}%. "
                "Prepare for batch discharge to prevent over-firing.",
            ))

        # ③ Stewing risk (bed_temp < 70 °C for > 2 min)
        if self.bed_temp < 70:
            self._low_temp_accum += dt
            if self._low_temp_accum > 2.0 and self._can_fire("stewing", 3.0):
                alerts.append(CoPilotAlert(
                    time=self.t, severity="danger", tag="stewing",
                    title="Stewing Risk Detected",
                    detail=f"Bed temp below 70°C for {self._low_temp_accum:.1f} min. "
                    "Theaflavin degradation likely. Increase Inlet Temp.",
                ))
        else:
            self._low_temp_accum = 0.0

        # ④ High SEC warning (energy inefficiency)
        if sec > 4.0 and self.t > 3.0 and self._can_fire("high_sec", 5.0):
            alerts.append(CoPilotAlert(
                time=self.t, severity="warning", tag="high_sec",
                title="Energy Efficiency Low",
                detail=f"SEC at {sec:.2f} kWh/kg — above 4.0 threshold. "
                "Consider increasing airflow or reducing temperature to improve efficiency.",
            ))

        # ⑤ Optimal phase suggestion (moisture 15-25%, enzyme < 50%)
        if (0.10 < self.moisture < 0.25 and self.enzyme < 0.5
                and self.bed_temp > 100 and self._can_fire("opt_phase", 5.0)):
            alerts.append(CoPilotAlert(
                time=self.t, severity="info", tag="opt_phase",
                title="Optimal: Reduce Temperature",
                detail=f"Moisture at {self.moisture*100:.1f}%, enzyme fixed at {self.enzyme*100:.0f}%. "
                "Gentle drying at 90-95°C saves energy with minimal quality impact.",
            ))

        # ⑥ Drying cycle started
        if self.t <= (self.cfg.dt + 0.01) and self._can_fire("start", 999):
            alerts.append(CoPilotAlert(
                time=self.t, severity="info", tag="start",
                title="Drying Cycle Initiated",
                detail=f"Batch: {self.cfg.batch_size_kg:.0f} kg wet tea. "
                f"Target: {self.cfg.me*100:.0f}% moisture. Monitoring all parameters.",
            ))

        return alerts

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
                  dt: float | None = None,
                  power_kw: float = 0.0,
                  energy_kwh: float = 0.0,
                  operating_cost_inr: float = 0.0,
                  sec: float = 0.0,
                  water_removed_kg: float = 0.0,
                  batch_value_inr: float = 0.0,
                  alerts: List[CoPilotAlert] | None = None) -> DryerState:
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
            power_kw=power_kw,
            energy_kwh=energy_kwh,
            operating_cost_inr=operating_cost_inr,
            sec=sec,
            water_removed_kg=water_removed_kg,
            batch_value_inr=batch_value_inr,
            sensors=sensor_rd,
            alerts=alerts or [],
        )

    # ─── convenience ──────────────────────────────────────
    def snapshot_dict(self) -> Dict[str, Any]:
        """Current state as a JSON-ready dict."""
        return self.history[-1].to_dict() if self.history else {}

    def history_dicts(self) -> List[Dict[str, Any]]:
        """Full history as a list of JSON-ready dicts."""
        return [s.to_dict() for s in self.history]
