"""
sensors.py — Synthetic sensor simulation layer for AuraSense.

Simulates four sensor subsystems that would be part of the physical retrofit
kit, each producing realistic noisy signals derived from the ground-truth
physics state:

    1. Electronic Nose  (e-Nose)  — 8 virtual MOS gas sensors
    2. Thermocouple Array         — 3-zone temperature readings
    3. Humidity Sensor             — exhaust-air RH
    4. Colorimeter Camera          — top-down CIELAB / RGB readings

All sensors add:
    • Gaussian measurement noise (configurable σ)
    • Realistic response characteristics (lag, drift, saturation)
    • Occasional spatial variation (camera samples multiple bed points)

The `SensorSuite` class wraps all four into a single `.read()` call that
returns a `SensorReading` dataclass — the observation vector the RL agent
and frontend will consume.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any

from backend.config import SimConfig
from backend.simulation.color import lab_to_rgb, lab_to_hex


# ═══════════════════════════════════════════════════════════
# Data containers
# ═══════════════════════════════════════════════════════════

@dataclass
class ENoseReading:
    """8-channel MOS gas-sensor voltage array."""
    voltages: List[float]          # one per sensor channel (V)
    voc_index: float               # composite VOC index (0–100 scale)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voltages": [round(v, 4) for v in self.voltages],
            "voc_index": round(self.voc_index, 2),
        }


@dataclass
class ThermocoupleReading:
    """3-zone temperature measurement."""
    inlet: float    # °C
    bed: float      # °C
    exhaust: float  # °C

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inlet": round(self.inlet, 2),
            "bed": round(self.bed, 2),
            "exhaust": round(self.exhaust, 2),
        }


@dataclass
class HumidityReading:
    """Exhaust-side relative humidity."""
    rh_percent: float       # %RH
    dewpoint_c: float       # °C  (derived)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rh_percent": round(self.rh_percent, 2),
            "dewpoint_c": round(self.dewpoint_c, 2),
        }


@dataclass
class ColorimeterReading:
    """Top-down camera colour measurement (CIELAB + RGB)."""
    l_star: float
    a_star: float
    b_star: float
    rgb: Tuple[int, int, int]
    hex_color: str
    uniformity: float       # 0–1 — how uniform the bed colour is

    def to_dict(self) -> Dict[str, Any]:
        return {
            "l_star": round(self.l_star, 2),
            "a_star": round(self.a_star, 2),
            "b_star": round(self.b_star, 2),
            "rgb": list(self.rgb),
            "hex_color": self.hex_color,
            "uniformity": round(self.uniformity, 3),
        }


@dataclass
class SensorReading:
    """Aggregated reading from all four sensor subsystems."""
    time: float
    enose: ENoseReading
    thermocouple: ThermocoupleReading
    humidity: HumidityReading
    colorimeter: ColorimeterReading

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": round(self.time, 3),
            "enose": self.enose.to_dict(),
            "thermocouple": self.thermocouple.to_dict(),
            "humidity": self.humidity.to_dict(),
            "colorimeter": self.colorimeter.to_dict(),
        }

    def flat_observation(self) -> List[float]:
        """
        Flat numeric vector for RL observation space.
        Order: [8× e-nose voltages, voc_index, T_inlet, T_bed, T_exhaust,
                RH, L*, a*, b*, uniformity]   →  17 floats
        """
        e = self.enose
        t = self.thermocouple
        h = self.humidity
        c = self.colorimeter
        return (
            e.voltages
            + [e.voc_index,
               t.inlet, t.bed, t.exhaust,
               h.rh_percent,
               c.l_star, c.a_star, c.b_star,
               c.uniformity]
        )


# ═══════════════════════════════════════════════════════════
# 1. Electronic Nose  (e-Nose)
# ═══════════════════════════════════════════════════════════

# Sensitivity profiles for 8 virtual MOS sensors.
# Each row: (moisture_weight, enzyme_weight, pyrazine_weight, temp_weight)
# Roughly modelled after TGS 2600/2602/2610/2611/2620 family.
_ENOSE_PROFILES = [
    # S0: broad VOC — responds to everything
    (0.30, 0.30, 0.25, 0.15),
    # S1: moisture-dominant (like TGS 2600 — air contaminants)
    (0.70, 0.10, 0.05, 0.15),
    # S2: oxidation products (catechin → theaflavin off-gassing)
    (0.10, 0.65, 0.10, 0.15),
    # S3: pyrazine / Maillard volatiles
    (0.05, 0.05, 0.75, 0.15),
    # S4: humidity-coupled (moisture + temp)
    (0.50, 0.05, 0.05, 0.40),
    # S5: fermentation marker (enzyme + moisture)
    (0.35, 0.50, 0.05, 0.10),
    # S6: roast detector (pyrazine + temp)
    (0.05, 0.05, 0.55, 0.35),
    # S7: residual green-leaf VOC (inversely correlated with drying)
    (0.60, 0.15, 0.05, 0.20),
]


class ENoseSensor:
    """Simulated 8-channel MOS electronic nose."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.n = cfg.enose_num_sensors
        # per-channel baseline drift accumulators
        self._drift = [0.0] * self.n

    def read(self, moisture: float, enzyme_activity: float,
             pyrazine: float, bed_temp_c: float,
             elapsed_min: float) -> ENoseReading:
        """
        Generate synthetic e-nose voltages from ground-truth state.

        The mapping:
            voltage = baseline + sum(weight_i · feature_i) + drift + noise
        where features are normalised to [0, 1].
        """
        cfg = self.cfg

        # Normalise features to 0–1 range
        f_moist = moisture / 0.70               # 0.70 = max expected
        f_enzyme = enzyme_activity                # already 0–1
        f_pyrazine = min(pyrazine / 3.0, 1.0)     # 3.0 µg/g = saturation proxy
        f_temp = min(bed_temp_c / 130.0, 1.0)   # 130 °C = practical max

        features = [f_moist, f_enzyme, f_pyrazine, f_temp]
        vrange = cfg.enose_max_v - cfg.enose_baseline_v  # dynamic range

        voltages: List[float] = []
        for ch in range(self.n):
            profile = _ENOSE_PROFILES[ch]
            # Weighted sum of features
            signal = sum(w * f for w, f in zip(profile, features))
            # Scale to voltage range
            v = cfg.enose_baseline_v + signal * vrange
            # Add drift (accumulates over time)
            self._drift[ch] += cfg.enose_drift_rate * \
                (cfg.dt if elapsed_min > 0 else 0)
            v += self._drift[ch]
            # Add Gaussian noise
            v += random.gauss(0, cfg.enose_noise_std)
            # Clamp to ADC range
            v = max(0.0, min(cfg.enose_max_v, v))
            voltages.append(v)

        # Composite VOC index: RMS of all channels, scaled to 0–100
        rms = math.sqrt(sum(v ** 2 for v in voltages) / self.n)
        voc_index = (rms / cfg.enose_max_v) * 100.0

        return ENoseReading(voltages=voltages, voc_index=voc_index)

    def reset(self) -> None:
        self._drift = [0.0] * self.n


# ═══════════════════════════════════════════════════════════
# 2. Thermocouple Array
# ═══════════════════════════════════════════════════════════

class ThermocoupleArray:
    """Simulated 3-zone thermocouple readings (inlet, bed, exhaust)."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self._exhaust_temp = cfg.ambient_temp  # lagged exhaust value

    def read(self, inlet_temp: float, bed_temp: float,
             dt: float) -> ThermocoupleReading:
        """
        Produce noisy temperature readings.

        Exhaust temp = bed_temp − ΔT_drop, with its own first-order lag.
        """
        cfg = self.cfg
        noise = cfg.tc_noise_std

        # Exhaust temperature: bed minus drop, with lag
        target_exhaust = bed_temp - cfg.tc_exhaust_drop
        tau = cfg.tc_exhaust_lag_tau
        if tau > 0 and dt > 0:
            alpha = dt / tau
            self._exhaust_temp += alpha * (target_exhaust - self._exhaust_temp)
        else:
            self._exhaust_temp = target_exhaust

        return ThermocoupleReading(
            inlet=inlet_temp + random.gauss(0, noise),
            bed=bed_temp + random.gauss(0, noise),
            exhaust=self._exhaust_temp + random.gauss(0, noise),
        )

    def reset(self) -> None:
        self._exhaust_temp = self.cfg.ambient_temp


# ═══════════════════════════════════════════════════════════
# 3. Humidity Sensor
# ═══════════════════════════════════════════════════════════

def _saturation_pressure(temp_c: float) -> float:
    """
    Antoine equation for water saturation pressure (hPa).
    Valid for 1–100 °C.
    """
    return 6.1078 * 10 ** ((7.5 * temp_c) / (237.3 + temp_c))


class HumiditySensor:
    """
    Simulated exhaust-air humidity sensor.

    Derives RH from a simplified mass balance:
        • More moisture evaporating → higher exhaust RH
        • Hotter exhaust → lower RH (same absolute humidity, higher Psat)
    """

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg

    def read(self, moisture: float, drying_rate: float,
             exhaust_temp: float) -> HumidityReading:
        """
        Parameters
        ----------
        moisture : float      Current moisture (wet-basis fraction).
        drying_rate : float   dM/dt (negative when drying).
        exhaust_temp : float  Exhaust thermocouple reading (°C).
        """
        cfg = self.cfg

        # Evaporation intensity → absolute humidity contribution
        # drying_rate is negative; take abs for magnitude
        evap_rate = abs(drying_rate)

        # Map evaporation to an RH boost above ambient
        #   At peak drying (~0.03 frac/min) → +20 %RH above ambient
        rh_boost = min(evap_rate / 0.03, 1.0) * 20.0

        # Base RH drops as exhaust gets hotter (Psat rises)
        if exhaust_temp > 30:
            temp_suppression = max(0, (exhaust_temp - 30) * 0.3)
        else:
            temp_suppression = 0.0

        rh = cfg.rh_ambient + rh_boost - temp_suppression
        rh = max(5.0, min(99.0, rh))

        # Add noise
        rh += random.gauss(0, cfg.rh_noise_std)
        rh = max(0.0, min(100.0, rh))

        # Dewpoint approximation (Magnus formula)
        gamma = math.log(rh / 100.0) + (17.67 * exhaust_temp) / \
            (243.5 + exhaust_temp)
        dewpoint = (243.5 * gamma) / (17.67 - gamma)

        return HumidityReading(rh_percent=rh, dewpoint_c=dewpoint)


# ═══════════════════════════════════════════════════════════
# 4. Colorimeter Camera
# ═══════════════════════════════════════════════════════════

class ColorimeterCamera:
    """
    Simulated top-down camera capturing the tea-bed surface colour.

    Takes multiple spatial samples across the bed to model the fact that
    real beds aren't perfectly uniform — edges dry faster than the centre.
    Returns the mean CIELAB values plus a uniformity score.
    """

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg

    def read(self, l_star: float, a_star: float,
             b_star: float) -> ColorimeterReading:
        """
        Parameters are ground-truth CIELAB values from the physics engine.
        """
        cfg = self.cfg
        n = cfg.cam_sample_points

        # Simulate spatial variation across the bed
        # Centre dries slower (slightly lighter), edges faster (slightly darker)
        l_samples: List[float] = []
        a_samples: List[float] = []
        b_samples: List[float] = []

        for i in range(n):
            # Spatial offset: centre (i=n//2) → 0, edges → ±1
            frac = (i - (n - 1) / 2) / max((n - 1) / 2, 1)
            # Edges are ~2 L* units darker (more dried)
            spatial_offset_l = -1.5 * abs(frac)
            spatial_offset_a = 0.8 * abs(frac)   # edges slightly more red
            spatial_offset_b = -0.5 * abs(frac)  # edges slightly less yellow

            l_samples.append(l_star + spatial_offset_l +
                             random.gauss(0, cfg.cam_noise_std_l))
            a_samples.append(a_star + spatial_offset_a +
                             random.gauss(0, cfg.cam_noise_std_ab))
            b_samples.append(b_star + spatial_offset_b +
                             random.gauss(0, cfg.cam_noise_std_ab))

        # Mean across samples
        mean_l = sum(l_samples) / n
        mean_a = sum(a_samples) / n
        mean_b = sum(b_samples) / n

        # Uniformity = 1 − normalised std of L* samples
        if n > 1:
            std_l = math.sqrt(
                sum((x - mean_l) ** 2 for x in l_samples) / (n - 1))
            uniformity = max(0.0, 1.0 - std_l / 5.0)  # 5.0 = scaling factor
        else:
            uniformity = 1.0

        rgb = lab_to_rgb(mean_l, mean_a, mean_b)
        hex_col = lab_to_hex(mean_l, mean_a, mean_b)

        return ColorimeterReading(
            l_star=mean_l,
            a_star=mean_a,
            b_star=mean_b,
            rgb=rgb,
            hex_color=hex_col,
            uniformity=uniformity,
        )


# ═══════════════════════════════════════════════════════════
# 5. Sensor Suite  (Fusion Aggregator)
# ═══════════════════════════════════════════════════════════

class SensorSuite:
    """
    Wraps all four sensor subsystems into a single `.read()` call.

    Usage
    -----
        suite = SensorSuite(cfg)
        reading = suite.read(dryer_state)   # returns SensorReading
        obs = reading.flat_observation()    # 17-float vector for RL
    """

    def __init__(self, cfg: SimConfig | None = None) -> None:
        self.cfg = cfg or SimConfig()
        self.enose = ENoseSensor(self.cfg)
        self.thermocouples = ThermocoupleArray(self.cfg)
        self.humidity = HumiditySensor(self.cfg)
        self.colorimeter = ColorimeterCamera(self.cfg)

    def read(self, *, time: float, moisture: float, enzyme_activity: float,
             pyrazine: float, bed_temp: float, inlet_temp: float,
             drying_rate: float, l_star: float, a_star: float,
             b_star: float, dt: float) -> SensorReading:
        """
        Take a synchronized reading from all sensors.

        Parameters mirror the DryerState fields — pass them directly
        from the physics engine snapshot.
        """
        enose_rd = self.enose.read(
            moisture=moisture,
            enzyme_activity=enzyme_activity,
            pyrazine=pyrazine,
            bed_temp_c=bed_temp,
            elapsed_min=time,
        )

        tc_rd = self.thermocouples.read(
            inlet_temp=inlet_temp,
            bed_temp=bed_temp,
            dt=dt,
        )

        humidity_rd = self.humidity.read(
            moisture=moisture,
            drying_rate=drying_rate,
            exhaust_temp=tc_rd.exhaust,
        )

        color_rd = self.colorimeter.read(
            l_star=l_star,
            a_star=a_star,
            b_star=b_star,
        )

        return SensorReading(
            time=time,
            enose=enose_rd,
            thermocouple=tc_rd,
            humidity=humidity_rd,
            colorimeter=color_rd,
        )

    def reset(self) -> None:
        """Reset all sensor internal state (drift, lag accumulators)."""
        self.enose.reset()
        self.thermocouples.reset()
