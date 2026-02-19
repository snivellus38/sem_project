"""
moisture.py — Page Model for thin-layer drying of CTC tea.

The Page equation is an empirical modification of Newton's law of cooling
applied to moisture transfer:

    MR(t) = exp(-k · t^n)

where
    MR  = (M(t) - Me) / (M0 - Me)   — moisture ratio (dimensionless)
    M(t)                             — moisture at time t  (wet-basis fraction)
    M0                               — initial moisture
    Me                               — equilibrium moisture
    k, n                             — fitted drying parameters

The effective drying constant `k` is modulated by inlet temperature and
airflow so that hotter / faster air dries the tea more quickly — matching
real FBD behaviour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.config import SimConfig


# ──────────────────────────────────────────────────────────
# Helper: temperature & airflow modifier on drying rate
# ──────────────────────────────────────────────────────────
def _effective_k(base_k: float, inlet_temp: float, airflow: float) -> float:
    """
    Scale the Page drying constant by process conditions.

    Heuristic (based on Arrhenius-like sensitivity):
        k_eff = base_k · (T_inlet / 100)^1.5 · airflow^0.6

    At the reference point (100 °C, airflow = 1.0), k_eff == base_k.
    """
    temp_factor = (inlet_temp / 100.0) ** 1.5
    air_factor = max(airflow, 0.05) ** 0.6      # clamp to avoid zero
    return base_k * temp_factor * air_factor


# ──────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────
def moisture_ratio(t: float, k_eff: float, n: float) -> float:
    """Return the dimensionless Moisture Ratio at elapsed time `t` (min)."""
    if t <= 0.0:
        return 1.0
    return math.exp(-k_eff * (t ** n))


def moisture_content(t: float, cfg: SimConfig,
                     inlet_temp: float | None = None,
                     airflow: float | None = None) -> float:
    """
    Return the absolute moisture content M(t) (wet-basis fraction)
    at elapsed time `t` minutes.

    Parameters
    ----------
    t : float          Elapsed drying time (minutes).
    cfg : SimConfig    Simulation configuration (carries M0, Me, k, n).
    inlet_temp : float Override inlet temperature (°C). Defaults to cfg value.
    airflow : float    Override airflow damper (0–1). Defaults to cfg value.
    """
    T = inlet_temp if inlet_temp is not None else cfg.inlet_temp
    af = airflow if airflow is not None else cfg.airflow
    k = _effective_k(cfg.page_k, T, af)
    mr = moisture_ratio(t, k, cfg.page_n)
    return cfg.me + (cfg.m0 - cfg.me) * mr


def drying_rate(t: float, cfg: SimConfig,
                inlet_temp: float | None = None,
                airflow: float | None = None) -> float:
    """
    Instantaneous drying rate  dM/dt  (fraction / min).

    Analytical derivative of the Page model:
        dM/dt = -(M0 - Me) · k · n · t^(n-1) · exp(-k · t^n)

    Returns a negative value (moisture is decreasing).
    """
    if t <= 0.0:
        return 0.0
    T = inlet_temp if inlet_temp is not None else cfg.inlet_temp
    af = airflow if airflow is not None else cfg.airflow
    k = _effective_k(cfg.page_k, T, af)
    n = cfg.page_n
    mr = moisture_ratio(t, k, n)
    return -(cfg.m0 - cfg.me) * k * n * (t ** (n - 1)) * mr
