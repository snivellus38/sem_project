"""
test_physics.py — Smoke test for the Phase 1 physics engine.

Run:  python -m backend.test_physics
"""

from backend.config import SimConfig
from backend.simulation.dryer import FBDSimulation


def test_default_drying_cycle():
    """Standard 30-minute cycle at 100 °C inlet, full airflow."""
    sim = FBDSimulation()
    history = sim.run()

    first, last = history[0], history[-1]
    assert first.moisture > 0.65,  f"Initial moisture too low: {first.moisture}"
    assert last.moisture < 0.06,  f"Final moisture too high: {last.moisture}"
    assert last.bed_temp > 95.0,  f"Bed never heated up: {last.bed_temp}"
    assert last.enzyme_activity < 0.01, "Enzyme should be fully denatured"
    assert last.l_star < first.l_star,   "Tea should darken over time"
    assert not last.stewing_penalty,     "No stewing at 100 °C inlet"
    print("[PASS] default_drying_cycle")


def test_high_temp_maillard():
    """At 130 °C inlet, Maillard pyrazines should form in the late stage."""
    cfg = SimConfig(inlet_temp=130.0, duration=30.0)
    sim = FBDSimulation(cfg)
    history = sim.run()

    last = history[-1]
    assert last.pyrazine > 0.0, \
        f"Expected pyrazine production at 130 °C inlet, got {last.pyrazine}"
    assert last.moisture < 0.05, f"Should be well-dried: {last.moisture}"
    print(f"[PASS] high_temp_maillard  (pyrazine = {last.pyrazine:.2f} µg/g)")


def test_low_temp_stewing():
    """At very low inlet temp, stewing penalty should trigger."""
    cfg = SimConfig(inlet_temp=55.0, duration=30.0)
    sim = FBDSimulation(cfg)
    history = sim.run()

    last = history[-1]
    assert last.stewing_penalty, \
        "Expected stewing penalty at 55 °C inlet"
    print("[PASS] low_temp_stewing")


def test_color_shift():
    """Color should go from greenish to dark brown."""
    sim = FBDSimulation()
    history = sim.run()

    first_hex = history[0].color_hex
    last_hex = history[-1].color_hex
    assert first_hex != last_hex, "Color should change during drying"
    assert history[-1].l_star < history[0].l_star, "L* should decrease"
    assert history[-1].a_star > history[0].a_star, "a* should increase (green→red)"
    print(f"[PASS] color_shift  ({first_hex} → {last_hex})")


def test_interactive_control():
    """Step-by-step with mid-run control change."""
    sim = FBDSimulation(SimConfig(duration=20.0))

    # Run first 10 min at default 100 °C
    for _ in range(100):  # 100 steps × 0.1 min = 10 min
        sim.step()
    mid = sim.history[-1]

    # Bump to 130 °C for final 10 min
    sim.set_controls(inlet_temp=130.0)
    while not sim.done:
        sim.step()
    last = sim.history[-1]

    assert last.bed_temp > mid.bed_temp, "Bed should be hotter after temp increase"
    print(
        f"[PASS] interactive_control  (T_bed: {mid.bed_temp:.1f} → {last.bed_temp:.1f} °C)")


if __name__ == "__main__":
    test_default_drying_cycle()
    test_high_temp_maillard()
    test_low_temp_stewing()
    test_color_shift()
    test_interactive_control()
    print("\n✅ All Phase 1 physics tests passed.")
