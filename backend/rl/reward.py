"""
reward.py — Multi-objective reward function for the RL agent.

The reward balances five competing objectives every time-step:

    1. Drying progress       (+)  Reward moisture reduction toward target
    2. Fuel economy          (−)  Penalise high inlet temperature
    3. Enzyme fixing         (+)  Reward rapid enzyme denaturation
    4. Stewing penalty       (−)  Heavy penalty for stewing (low temp + wet)
    5. Maillard bonus        (+)  Bonus when pyrazines are being produced
    6. Quality guard         (−)  Penalise over-drying (M < target) or over-
                                  darkening (L* too low)

Each component is scaled to roughly the same magnitude so no single term
dominates.  The weights can be tuned via RewardConfig.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class RewardConfig:
    """Tunable weights for each reward component."""
    w_drying:    float = 2.0      # weight for moisture reduction
    w_fuel:      float = 0.3      # weight for fuel penalty
    w_enzyme:    float = 1.0      # weight for enzyme denaturation
    w_stewing:   float = 5.0      # weight for stewing penalty (harsh)
    w_maillard:  float = 1.5      # weight for Maillard bonus
    w_overdry:   float = 2.0      # weight for over-drying penalty
    w_terminal:  float = 10.0     # weight for terminal quality bonus

    # Targets
    target_moisture: float = 0.04     # ideal final moisture (4% wb)
    target_l_star:   float = 24.0     # ideal final lightness
    # reference temp (penalty = 0 at this temp)
    fuel_ref_temp:   float = 100.0


def compute_reward(
    *,
    moisture: float,
    prev_moisture: float,
    bed_temp: float,
    inlet_temp: float,
    enzyme_activity: float,
    prev_enzyme: float,
    pyrazine: float,
    prev_pyrazine: float,
    l_star: float,
    stewing: bool,
    stewing_penalty: bool,
    done: bool,
    cfg: RewardConfig | None = None,
) -> tuple[float, Dict[str, float]]:
    """
    Compute the scalar reward and a breakdown dict for logging.

    Parameters are the current and previous state values.

    Returns
    -------
    (total_reward, components_dict)
    """
    c = cfg or RewardConfig()
    components: Dict[str, float] = {}

    # ── 1. Drying progress ────────────────────────────────
    # Positive reward for moisture reduction (dM is negative when drying)
    delta_m = prev_moisture - moisture          # positive when drying
    # scale up (values are tiny fracs)
    r_drying = c.w_drying * delta_m * 100
    components["drying"] = r_drying

    # ── 2. Fuel economy ───────────────────────────────────
    # Penalise temperatures above the reference; no penalty at or below ref
    temp_excess = max(0.0, inlet_temp - c.fuel_ref_temp) / 50.0   # normalised
    r_fuel = -c.w_fuel * temp_excess
    components["fuel"] = r_fuel

    # ── 3. Enzyme fixing ──────────────────────────────────
    # Reward enzyme kill (enzyme going from 1 → 0)
    delta_e = prev_enzyme - enzyme_activity     # positive when denaturing
    r_enzyme = c.w_enzyme * delta_e
    components["enzyme"] = r_enzyme

    # ── 4. Stewing penalty ────────────────────────────────
    r_stew = 0.0
    if stewing:
        r_stew -= c.w_stewing * 0.5             # per-tick penalty while in zone
    if stewing_penalty:
        r_stew -= c.w_stewing * 2.0             # extra hit when threshold crossed
    components["stewing"] = r_stew

    # ── 5. Maillard bonus ─────────────────────────────────
    delta_p = pyrazine - prev_pyrazine
    r_maillard = c.w_maillard * delta_p if delta_p > 0 else 0.0
    components["maillard"] = r_maillard

    # ── 6. Over-drying guard ──────────────────────────────
    r_overdry = 0.0
    if moisture < c.target_moisture - 0.01:
        # Penalise going too far below target
        overshoot = c.target_moisture - moisture
        r_overdry = -c.w_overdry * overshoot * 100
    components["overdry"] = r_overdry

    # ── 7. Terminal bonus / penalty ───────────────────────
    r_terminal = 0.0
    if done:
        # How close is final moisture to the target?
        m_err = abs(moisture - c.target_moisture)
        if m_err < 0.01:
            r_terminal += c.w_terminal * 1.0         # within 1% → full bonus
        elif m_err < 0.03:
            r_terminal += c.w_terminal * 0.5         # within 3%
        else:
            r_terminal -= c.w_terminal * m_err * 10  # far off → penalty

        # Enzyme should be fully dead by end
        if enzyme_activity < 0.01:
            r_terminal += c.w_terminal * 0.3
        else:
            r_terminal -= c.w_terminal * enzyme_activity

        # Stewing should not have triggered
        if stewing_penalty:
            r_terminal -= c.w_terminal * 1.5

        # Bonus for any pyrazine production (flavor complexity)
        if pyrazine > 0.1:
            r_terminal += c.w_terminal * 0.2

    components["terminal"] = r_terminal

    # ── Total ─────────────────────────────────────────────
    total = sum(components.values())
    components["total"] = total

    return total, components
