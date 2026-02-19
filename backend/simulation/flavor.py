"""
flavor.py — Zero-order Maillard reaction kinetics for pyrazine generation.

Model
-----
Pyrazines (roasty / toasty flavor compounds) form via the Maillard reaction
between amino acids and reducing sugars at elevated temperatures and low
moisture.  In the drying context the reaction only proceeds meaningfully when:

    1. Bed temperature  >  T_maillard_min   (default 110 °C)
    2. Moisture content  <  M_maillard_max   (default 10 % wb)

When both conditions are satisfied the generation rate is constant
(zero-order):

    dP/dt = k_maillard          (µg pyrazine / g dry matter / min)

Below the thresholds, dP/dt = 0.

The zero-order assumption is reasonable because both substrates (amino acids,
sugars) are in large excess relative to the tiny mass of pyrazines produced.
"""

from __future__ import annotations

from backend.config import SimConfig


def maillard_rate(bed_temp_c: float, moisture: float,
                  cfg: SimConfig) -> float:
    """
    Return the instantaneous pyrazine generation rate (µg/g/min).

    Zero when either threshold is not met.
    """
    if bed_temp_c >= cfg.maillard_temp_min and moisture <= cfg.maillard_moist_max:
        return cfg.maillard_k
    return 0.0


def step_flavor(pyrazine: float, bed_temp_c: float, moisture: float,
                dt: float, cfg: SimConfig) -> float:
    """
    Advance pyrazine accumulation by one time-step (explicit Euler).

    Parameters
    ----------
    pyrazine : float    Current cumulative pyrazine (µg/g dry matter).
    bed_temp_c : float  Tea-bed temperature (°C).
    moisture : float    Current moisture (wet-basis fraction).
    dt : float          Time-step (minutes).
    cfg : SimConfig     Configuration.

    Returns the updated pyrazine value (always >= 0).
    """
    dp = maillard_rate(bed_temp_c, moisture, cfg) * dt
    return pyrazine + dp
