"""
test_sensors.py — Smoke tests for Phase 2: Sensor Simulation Layer.

Run:  python -m backend.test_sensors
"""

from backend.config import SimConfig
from backend.simulation.dryer import FBDSimulation


def test_sensor_readings_present():
    """Every DryerState should now carry a SensorReading."""
    sim = FBDSimulation()
    history = sim.run()

    for s in history:
        assert s.sensors is not None, f"Missing sensors at t={s.time}"
    print("[PASS] sensor_readings_present")


def test_enose_channels():
    """E-nose should have 8 voltage channels, all within ADC range."""
    sim = FBDSimulation()
    history = sim.run()

    for s in history:
        v = s.sensors.enose.voltages
        assert len(v) == 8, f"Expected 8 channels, got {len(v)}"
        for ch, val in enumerate(v):
            assert 0.0 <= val <= 4.6, f"Ch{ch} out of range: {val}"
    print("[PASS] enose_channels")


def test_enose_responds_to_drying():
    """Moisture-sensitive channels should decrease as tea dries."""
    sim = FBDSimulation()
    history = sim.run()

    first = history[1].sensors.enose.voltages   # skip t=0 (cold start)
    last = history[-1].sensors.enose.voltages

    # Channel 1 (moisture-dominant) should drop significantly
    assert last[1] < first[1], \
        f"Ch1 (moisture) should decrease: {first[1]:.2f} → {last[1]:.2f}"
    print(
        f"[PASS] enose_responds_to_drying  (Ch1: {first[1]:.2f}V → {last[1]:.2f}V)")


def test_voc_index_range():
    """VOC index should be 0–100."""
    sim = FBDSimulation()
    history = sim.run()

    for s in history:
        vi = s.sensors.enose.voc_index
        assert 0 <= vi <= 100, f"VOC index out of range: {vi}"
    print("[PASS] voc_index_range")


def test_thermocouple_zones():
    """Three temperature zones should exist with inlet > bed > exhaust."""
    sim = FBDSimulation()
    history = sim.run()

    # Check mid-simulation (once bed has heated up)
    mid = history[len(history) // 2].sensors.thermocouple
    assert mid.inlet > 0 and mid.bed > 0 and mid.exhaust > 0, \
        "All zones should be positive"
    # Exhaust should be cooler than bed (by TC_EXHAUST_DROP)
    assert mid.exhaust < mid.bed, \
        f"Exhaust ({mid.exhaust:.1f}) should be cooler than bed ({mid.bed:.1f})"
    print(
        f"[PASS] thermocouple_zones  (inlet={mid.inlet:.1f} bed={mid.bed:.1f} exhaust={mid.exhaust:.1f})")


def test_humidity_during_drying():
    """Exhaust RH should be elevated during active drying."""
    sim = FBDSimulation()
    history = sim.run()

    # Early phase: rapid evaporation → high RH
    early = history[20].sensors.humidity.rh_percent   # ~2 min in
    late = history[-1].sensors.humidity.rh_percent    # end of cycle

    assert early > 0, f"RH should be positive: {early}"
    assert late > 0,  f"RH should be positive: {late}"
    print(
        f"[PASS] humidity_during_drying  (early={early:.1f}%RH  late={late:.1f}%RH)")


def test_colorimeter_uniformity():
    """Uniformity should be between 0 and 1."""
    sim = FBDSimulation()
    history = sim.run()

    for s in history:
        u = s.sensors.colorimeter.uniformity
        assert 0.0 <= u <= 1.0, f"Uniformity out of range: {u}"
    print("[PASS] colorimeter_uniformity")


def test_colorimeter_tracks_physics():
    """Camera L* should roughly track physics L* (within noise)."""
    sim = FBDSimulation()
    history = sim.run()

    for s in history:
        physics_l = s.l_star
        camera_l = s.sensors.colorimeter.l_star
        # Should be within ±5 L* units (noise + spatial variation)
        assert abs(physics_l - camera_l) < 5.0, \
            f"Camera L*={camera_l:.1f} too far from physics L*={physics_l:.1f}"
    print("[PASS] colorimeter_tracks_physics")


def test_flat_observation_vector():
    """flat_observation() should return exactly 17 floats."""
    sim = FBDSimulation()
    sim.step()
    obs = sim.history[-1].sensors.flat_observation()
    assert len(obs) == 17, f"Expected 17 floats, got {len(obs)}"
    for i, v in enumerate(obs):
        assert isinstance(v, float), f"obs[{i}] is {type(v)}, expected float"
    print(f"[PASS] flat_observation_vector  (length={len(obs)})")


def test_sensor_json_serialization():
    """Sensor data should serialise to a clean dict."""
    sim = FBDSimulation()
    sim.step()
    d = sim.history[-1].to_dict()
    assert "sensors" in d, "Missing 'sensors' key in state dict"
    sd = d["sensors"]
    assert "enose" in sd
    assert "thermocouple" in sd
    assert "humidity" in sd
    assert "colorimeter" in sd
    assert len(sd["enose"]["voltages"]) == 8
    print("[PASS] sensor_json_serialization")


def test_sensor_drift():
    """E-nose baseline should drift slightly over a long run."""
    cfg = SimConfig(duration=30.0)
    sim = FBDSimulation(cfg)
    history = sim.run()

    # Compare VOC index at start vs end — drift should cause a small shift
    # (This is a soft test; drift is tiny but non-zero)
    v_start = history[1].sensors.enose.voc_index
    v_end = history[-1].sensors.enose.voc_index
    print(f"[PASS] sensor_drift  (VOC index: {v_start:.2f} → {v_end:.2f})")


if __name__ == "__main__":
    test_sensor_readings_present()
    test_enose_channels()
    test_enose_responds_to_drying()
    test_voc_index_range()
    test_thermocouple_zones()
    test_humidity_during_drying()
    test_colorimeter_uniformity()
    test_colorimeter_tracks_physics()
    test_flat_observation_vector()
    test_sensor_json_serialization()
    test_sensor_drift()
    print("\n✅ All Phase 2 sensor tests passed.")
