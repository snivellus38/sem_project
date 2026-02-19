"""
color.py — CIELAB color-space model for tea-leaf appearance during drying.

Model
-----
As CTC tea dries, it transitions visually from a damp, greenish-copper to a
dry, dark brown / black.  We model all three CIELAB channels:

    L*(t)  = L_min   + (L0 - L_min)   · exp(-λ_L · t)     (lightness ↓)
    a*(t)  = a_final - (a_final - a0)  · exp(-λ_a · t)     (green → red ↑)
    b*(t)  = b_final + (b0 - b_final)  · exp(-λ_b · t)     (yellow ↓)

The decay rates (λ) are boosted when the bed is hotter and the moisture is
still high enough for browning reactions (enzymatic + non-enzymatic) to
proceed rapidly.

CIELAB → sRGB conversion is also provided so the frontend can directly colour
3D meshes.
"""

from __future__ import annotations

import math
from typing import Tuple

from backend.config import SimConfig


# ──────────────────────────────────────────────────────────
# Core CIELAB channel values (analytical, time-domain)
# ──────────────────────────────────────────────────────────
def _temp_color_factor(bed_temp_c: float) -> float:
    """
    Scaling factor [0.5 … 2.0] — hotter bed accelerates browning.
    Normalised so factor = 1.0 at 100 °C.
    """
    return max(0.5, min(2.0, (bed_temp_c / 100.0) ** 1.2))


def l_star(t: float, bed_temp_c: float, cfg: SimConfig) -> float:
    """Lightness L*(t) — decays from L0 toward L_min."""
    lam = cfg.lambda_l * _temp_color_factor(bed_temp_c)
    return cfg.l_min + (cfg.l0 - cfg.l_min) * math.exp(-lam * t)


def a_star(t: float, bed_temp_c: float, cfg: SimConfig) -> float:
    """a*(t) — rises from a0 (green) toward a_final (red/brown)."""
    lam = cfg.lambda_a * _temp_color_factor(bed_temp_c)
    return cfg.a_final - (cfg.a_final - cfg.a0) * math.exp(-lam * t)


def b_star(t: float, bed_temp_c: float, cfg: SimConfig) -> float:
    """b*(t) — drops from b0 (yellow) toward b_final (brown)."""
    lam = cfg.lambda_b * _temp_color_factor(bed_temp_c)
    return cfg.b_final + (cfg.b0 - cfg.b_final) * math.exp(-lam * t)


def lab(t: float, bed_temp_c: float, cfg: SimConfig) -> Tuple[float, float, float]:
    """Return (L*, a*, b*) tuple at time t."""
    return (
        l_star(t, bed_temp_c, cfg),
        a_star(t, bed_temp_c, cfg),
        b_star(t, bed_temp_c, cfg),
    )


# ──────────────────────────────────────────────────────────
# CIELAB → sRGB conversion  (D65 illuminant)
#   Used by the frontend to colour the 3D tea-bed mesh.
# ──────────────────────────────────────────────────────────
# D65 white-point tristimulus values
_XN, _YN, _ZN = 95.047, 100.0, 108.883


def _lab_to_xyz(L: float, a: float, b: float) -> Tuple[float, float, float]:
    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    def _inv_f(t: float) -> float:
        delta = 6.0 / 29.0
        if t > delta:
            return t ** 3
        return 3.0 * delta * delta * (t - 4.0 / 29.0)

    X = _XN * _inv_f(fx)
    Y = _YN * _inv_f(fy)
    Z = _ZN * _inv_f(fz)
    return X, Y, Z


def _linear_to_srgb(c: float) -> float:
    """Apply sRGB gamma curve to a single linear channel."""
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def lab_to_rgb(L: float, a: float, b: float) -> Tuple[int, int, int]:
    """
    Convert CIELAB (D65) → sRGB (0–255 per channel).

    Returns clamped integer (R, G, B).
    """
    X, Y, Z = _lab_to_xyz(L, a, b)
    # XYZ → linear sRGB  (IEC 61966-2-1 matrix, D65)
    x, y, z = X / 100.0, Y / 100.0, Z / 100.0
    r_lin = 3.2406 * x - 1.5372 * y - 0.4986 * z
    g_lin = -0.9689 * x + 1.8758 * y + 0.0415 * z
    b_lin = 0.0557 * x - 0.2040 * y + 1.0570 * z

    r = _linear_to_srgb(r_lin)
    g = _linear_to_srgb(g_lin)
    b_ = _linear_to_srgb(b_lin)

    def clamp(v): return max(0, min(255, int(round(v * 255))))
    return clamp(r), clamp(g), clamp(b_)


def lab_to_hex(L: float, a: float, b: float) -> str:
    """Convert CIELAB → hex string  (#RRGGBB)."""
    r, g, b_ = lab_to_rgb(L, a, b)
    return f"#{r:02x}{g:02x}{b_:02x}"
