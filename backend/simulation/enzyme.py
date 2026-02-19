"""
enzyme.py — Arrhenius first-order kinetics for polyphenol oxidase (PPO)
inactivation during tea drying.

Model
-----
Polyphenol oxidase catalyses oxidation of catechins → theaflavins / thearubigins
during the fermentation stage.  Once the leaf enters the dryer the goal is to
*fix* (halt) this reaction by thermally denaturing the enzyme.

    dC/dt  = -A · exp(-Ea / (R·T_bed)) · C

where
    C       — normalised residual enzyme activity  (1 = fully active, 0 = dead)
    A       — pre-exponential (frequency) factor   (s⁻¹)
    Ea      — activation energy                    (J/mol)
    R       — universal gas constant               (8.314 J/(mol·K))
    T_bed   — tea-bed temperature                  (K)

Stewing
-------
If the bed temperature stays *too low* while the leaf is still wet, oxidation
continues uncontrolled and the tea "stews" — resulting in a dull, flat liquor.

We track cumulative stewing time and expose a penalty flag when it exceeds the
configured threshold.
"""

from __future__ import annotations

import math

from backend.config import R_GAS, SimConfig


# ──────────────────────────────────────────────────────────
# Core rate
# ──────────────────────────────────────────────────────────
def denaturation_rate(enzyme_activity: float, bed_temp_c: float,
                      cfg: SimConfig) -> float:
    """
    Instantaneous rate of enzyme denaturation  dC/dt  (per minute).

    Parameters
    ----------
    enzyme_activity : float   Current normalised activity [0, 1].
    bed_temp_c : float        Tea-bed temperature in °C.
    cfg : SimConfig           Carries A, Ea.

    Returns a *negative* value (activity is falling).
    """
    T_k = bed_temp_c + 273.15                           # convert to Kelvin
    k_rate = cfg.enzyme_a * math.exp(-cfg.enzyme_ea / (R_GAS * T_k))
    # k_rate is in s⁻¹; multiply by 60 to get per-minute
    return -k_rate * 60.0 * enzyme_activity


def step_enzyme(enzyme_activity: float, bed_temp_c: float,
                dt: float, cfg: SimConfig) -> float:
    """
    Advance enzyme activity by one time-step using explicit Euler.

    Returns the *new* enzyme activity, clamped to [0, 1].
    """
    dc = denaturation_rate(enzyme_activity, bed_temp_c, cfg) * dt
    return max(0.0, min(1.0, enzyme_activity + dc))


# ──────────────────────────────────────────────────────────
# Stewing tracker
# ──────────────────────────────────────────────────────────
class StewingTracker:
    """Accumulates time spent in the stewing danger zone and fires a flag."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.cumulative_minutes: float = 0.0
        self.is_stewing: bool = False      # currently in the zone right now
        self.penalty_triggered: bool = False

    def update(self, bed_temp_c: float, moisture: float, dt: float) -> None:
        """Call once per tick with current bed state."""
        in_zone = (bed_temp_c < self.cfg.stew_temp_ceil
                   and moisture > self.cfg.stew_moist_floor)
        self.is_stewing = in_zone
        if in_zone:
            self.cumulative_minutes += dt
        if self.cumulative_minutes >= self.cfg.stew_time_limit:
            self.penalty_triggered = True

    def reset(self) -> None:
        self.cumulative_minutes = 0.0
        self.is_stewing = False
        self.penalty_triggered = False
