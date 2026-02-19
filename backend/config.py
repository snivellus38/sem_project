"""
config.py — Physical constants, process defaults, and tunable parameters
for the AuraSense tea-drying simulation engine.

All values are sourced from published thin-layer drying studies on CTC
black tea and standard food-engineering references.  Units are SI unless
noted otherwise.
"""

from dataclasses import dataclass, field
from typing import Tuple

# ─────────────────────────────────────────────
# Universal constants
# ─────────────────────────────────────────────
R_GAS = 8.314          # J/(mol·K)  — universal gas constant


# ─────────────────────────────────────────────
# Page Model  (thin-layer moisture drying)
#   MR(t) = exp(-k · t^n)
#   MR  = (M - Me) / (M0 - Me)
# ─────────────────────────────────────────────
PAGE_K = 0.12          # drying constant  (min⁻¹, fitted for CTC tea @ ~100 °C)
PAGE_N = 1.04          # dimensionless exponent
M0 = 0.70          # initial moisture content  (wet-basis fraction, ~70 %)
ME = 0.03          # equilibrium moisture      (wet-basis fraction, ~3 %)


# ─────────────────────────────────────────────
# Arrhenius enzyme kinetics  (theaflavin fixing)
#   dC/dt = -A · exp(-Ea / (R·T)) · C
# ─────────────────────────────────────────────
ENZYME_A = 1.0e7     # pre-exponential factor   (s⁻¹)
ENZYME_EA = 45_000.0  # activation energy         (J/mol, ~45 kJ/mol for PPO)
C0_ENZYME = 1.0       # normalised initial enzyme activity (1.0 = fully active)

# Stewing penalty thresholds
STEW_TEMP_CEIL = 60.0   # °C  — bed temp below this is "stewing zone"
STEW_MOIST_FLOOR = 0.40   # wet-basis fraction above which stewing matters
STEW_TIME_LIMIT = 5.0    # minutes of continuous stewing before penalty


# ─────────────────────────────────────────────
# Maillard reaction  (pyrazine / roasty-note genesis)
#   dP/dt = k_maillard   (zero-order, only when conditions met)
# ─────────────────────────────────────────────
MAILLARD_K = 0.08   # µg pyrazine / g dry matter / min  (arbitrary scale)
MAILLARD_TEMP_MIN = 110.0  # °C  — onset temperature
MAILLARD_MOIST_MAX = 0.10  # wet-basis fraction — moisture must be below this


# ─────────────────────────────────────────────
# CIELAB color model  (first-order exponential decay)
#   L*(t)  = L_min + (L0 - L_min) · exp(-λ · t)
#   a*(t)  and  b*(t)  follow similar profiles
# ─────────────────────────────────────────────
L_STAR_0 = 52.0     # initial lightness (fresh rolled CTC leaf)
L_STAR_MIN = 22.0     # final lightness (well-dried black tea)
LAMBDA_L = 0.08     # decay rate for L*  (min⁻¹)

A_STAR_0 = -8.0     # initial a* (greenish)
A_STAR_FINAL = 12.0    # final a* (reddish-brown)
LAMBDA_A = 0.07     # decay rate for a*

B_STAR_0 = 25.0     # initial b* (yellowish)
B_STAR_FINAL = 10.0    # final b* (less yellow, more brown)
LAMBDA_B = 0.06     # decay rate for b*


# ─────────────────────────────────────────────
# Dryer operating defaults
# ─────────────────────────────────────────────
DEFAULT_INLET_TEMP = 100.0   # °C
DEFAULT_AIRFLOW = 1.0     # normalised (0–1 damper position)
BED_TEMP_LAG_TAU = 2.0     # minutes — first-order lag from inlet → bed temp
AMBIENT_TEMP = 28.0    # °C (Assam average)

# Simulation
SIM_DT = 0.1     # minutes per physics tick
SIM_DURATION = 30.0   # minutes — typical FBD drying cycle


# ─────────────────────────────────────────────
# Sensor simulation  (Phase 2)
# ─────────────────────────────────────────────

# Electronic Nose — 8 virtual MOS gas sensors
#   Each sensor has a characteristic sensitivity profile mapping
#   (moisture, enzyme_activity, pyrazine, bed_temp) → voltage.
#   We simulate realistic TGS-series MOS sensor curves.
ENOSE_NUM_SENSORS = 8
ENOSE_BASELINE_V = 0.4      # V — clean-air baseline voltage
ENOSE_MAX_V = 4.5      # V — saturation voltage
ENOSE_NOISE_STD = 0.02     # V — Gaussian sensor noise σ
ENOSE_DRIFT_RATE = 0.001    # V/min — slow baseline drift

# Thermocouple array — 3 zones (inlet, bed, exhaust)
TC_NOISE_STD = 0.5      # °C — measurement noise
TC_EXHAUST_DROP = 15.0     # °C — typical ΔT from bed → exhaust
TC_EXHAUST_LAG_TAU = 1.5      # min — exhaust thermocouple lag

# Humidity sensor — exhaust RH derived from moisture mass balance
RH_NOISE_STD = 1.5      # %RH — measurement noise
RH_AMBIENT = 75.0     # %RH — Assam ambient (high humidity)

# Colorimeter (camera) — simulates a top-down RGB camera
CAM_NOISE_STD_L = 0.8      # CIELAB L* noise
CAM_NOISE_STD_AB = 0.5      # CIELAB a*, b* noise
CAM_SAMPLE_POINTS = 5        # number of spatial sample points across bed


@dataclass
class SimConfig:
    """Runtime-overridable simulation configuration."""

    # Page model
    page_k: float = PAGE_K
    page_n: float = PAGE_N
    m0: float = M0
    me: float = ME

    # Enzyme
    enzyme_a: float = ENZYME_A
    enzyme_ea: float = ENZYME_EA
    c0_enzyme: float = C0_ENZYME

    # Maillard
    maillard_k: float = MAILLARD_K
    maillard_temp_min: float = MAILLARD_TEMP_MIN
    maillard_moist_max: float = MAILLARD_MOIST_MAX

    # Color
    l0: float = L_STAR_0
    l_min: float = L_STAR_MIN
    lambda_l: float = LAMBDA_L
    a0: float = A_STAR_0
    a_final: float = A_STAR_FINAL
    lambda_a: float = LAMBDA_A
    b0: float = B_STAR_0
    b_final: float = B_STAR_FINAL
    lambda_b: float = LAMBDA_B

    # Stewing thresholds
    stew_temp_ceil: float = STEW_TEMP_CEIL
    stew_moist_floor: float = STEW_MOIST_FLOOR
    stew_time_limit: float = STEW_TIME_LIMIT

    # Dryer
    inlet_temp: float = DEFAULT_INLET_TEMP
    airflow: float = DEFAULT_AIRFLOW
    bed_temp_lag_tau: float = BED_TEMP_LAG_TAU
    ambient_temp: float = AMBIENT_TEMP

    # Simulation
    dt: float = SIM_DT
    duration: float = SIM_DURATION

    # Sensors
    enose_num_sensors: int = ENOSE_NUM_SENSORS
    enose_baseline_v: float = ENOSE_BASELINE_V
    enose_max_v: float = ENOSE_MAX_V
    enose_noise_std: float = ENOSE_NOISE_STD
    enose_drift_rate: float = ENOSE_DRIFT_RATE
    tc_noise_std: float = TC_NOISE_STD
    tc_exhaust_drop: float = TC_EXHAUST_DROP
    tc_exhaust_lag_tau: float = TC_EXHAUST_LAG_TAU
    rh_noise_std: float = RH_NOISE_STD
    rh_ambient: float = RH_AMBIENT
    cam_noise_std_l: float = CAM_NOISE_STD_L
    cam_noise_std_ab: float = CAM_NOISE_STD_AB
    cam_sample_points: int = CAM_SAMPLE_POINTS
