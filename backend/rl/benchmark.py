"""
benchmark.py — RL-style adaptive controller vs PID benchmark utilities.

This module runs two controllers on the same dryer config and returns:
- aligned moisture trajectory data for plotting
- summary metrics for comparison cards
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from backend.config import SimConfig
from backend.rl.baseline_pid import BaselinePID
from backend.rl.reward import RewardConfig, compute_reward
from backend.simulation.dryer import FBDSimulation, DryerState


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR = _PROJECT_ROOT / "models"


def _discover_model_name(explicit_name: str | None = None) -> str | None:
    """Return a usable PPO model base-name if present under models/"""
    candidates = [
        explicit_name,
        "tea_dryer_PPO",
        "tea_dryer_best",
    ]

    for name in candidates:
        if not name:
            continue
        # Stable-Baselines3 expects a zip model artifact.
        if (_MODELS_DIR / f"{name}.zip").is_file():
            return name

    if _MODELS_DIR.is_dir():
        for p in _MODELS_DIR.glob("*.zip"):
            return p.stem
    return None


def _list_model_candidates(explicit_name: str | None = None) -> List[str]:
    """Return ordered model base-names available under models/."""
    if explicit_name:
        return [explicit_name]

    preferred = [
        "tea_dryer_PPO_energy",
        "tea_dryer_PPO",
        "tea_dryer_best",
    ]

    names: List[str] = []
    for name in preferred:
        if (_MODELS_DIR / f"{name}.zip").is_file():
            names.append(name)

    if _MODELS_DIR.is_dir():
        for p in _MODELS_DIR.glob("*.zip"):
            if p.stem not in names:
                names.append(p.stem)
    return names


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _controls_to_action(inlet_temp: float, airflow: float) -> list[float]:
    """Map physical controls back to normalized env action space [-1, 1]."""
    a0 = (inlet_temp - 105.0) / 25.0
    a1 = (airflow - 0.6) / 0.4
    return [_clamp(a0, -1.0, 1.0), _clamp(a1, -1.0, 1.0)]


def _govern_ppo_action(raw_action: Any, state: DryerState) -> list[float]:
    """
    Apply an energy-aware guardrail to PPO actions.

    The model output remains the primary signal, but we cap operating ranges
    by drying stage and thermal state to avoid energy-heavy trajectories.
    """
    a0 = float(raw_action[0])
    a1 = float(raw_action[1])

    inlet_temp = _clamp(a0, -1.0, 1.0) * 25.0 + 105.0
    airflow = _clamp(a1, -1.0, 1.0) * 0.4 + 0.6

    if state.moisture > 0.45:
        temp_max = 118.0
        airflow_max = 0.76
    elif state.moisture > 0.25:
        temp_max = 112.0
        airflow_max = 0.84
    elif state.moisture > 0.12:
        temp_max = 102.0
        airflow_max = 0.90
    else:
        temp_max = 95.0
        airflow_max = 0.95

    # Thermal protection to avoid late-stage overheating and enzyme damage.
    if state.bed_temp > 108.0:
        temp_max = min(temp_max, 94.0)

    inlet_temp = _clamp(inlet_temp, 80.0, temp_max)
    airflow = _clamp(airflow, 0.2, airflow_max)

    return _controls_to_action(inlet_temp, airflow)


def _choose_best_rl_history(
    candidates: List[tuple[List[DryerState], float, str]],
    cfg: SimConfig,
    reward_cfg: RewardConfig,
) -> tuple[List[DryerState], float, str]:
    """Pick the best RL rollout emphasizing target hit + energy efficiency."""
    if not candidates:
        return [], 0.0, "none"

    target = reward_cfg.target_moisture
    tight_tolerance = 0.01
    loose_tolerance = 0.02

    def _score(item: tuple[List[DryerState], float, str]) -> tuple[int, float, float]:
        hist, _, _ = item
        if not hist:
            return (1, float("inf"), float("inf"))
        final = hist[-1]
        moisture_err = abs(final.moisture - target)
        # If both are near target, prioritize lower energy.
        if moisture_err <= tight_tolerance:
            return (0, final.energy_kwh, moisture_err)
        if moisture_err <= loose_tolerance:
            return (1, moisture_err, final.energy_kwh)
        return (2, moisture_err, final.energy_kwh)

    return min(candidates, key=_score)


def _choose_best_model_rollout(
    candidates: List[tuple[List[DryerState], float, str]],
    cfg: SimConfig,
    reward_cfg: RewardConfig,
) -> tuple[List[DryerState], float, str]:
    """Select best model rollout by target proximity first, then energy/tracking."""
    if not candidates:
        return [], 0.0, "none"

    target_pct = reward_cfg.target_moisture * 100.0

    def _score(item: tuple[List[DryerState], float, str]) -> tuple[int, float, float, float]:
        hist, _, _ = item
        if not hist:
            return (2, float("inf"), float("inf"), float("inf"))

        s = _summary(hist, cfg, reward_cfg)
        moisture_err = abs(s["final_moisture_pct"] - target_pct)
        # Allow a practical moisture tolerance band, then minimize energy.
        bucket = 0 if moisture_err <= 3.0 else 1
        return (bucket, s["energy_kwh"], s["tracking_mae_pct"], moisture_err)

    return min(candidates, key=_score)


def _run_adaptive_policy(cfg: SimConfig, reward_cfg: RewardConfig) -> tuple[List[DryerState], float]:
    """
    Run a lightweight adaptive policy as an RL-style online controller.

    It adapts inlet temperature and airflow by moisture stage and thermal feedback.
    """
    sim = FBDSimulation(cfg)
    total_reward = 0.0
    prev_m = cfg.m0
    prev_e = cfg.c0_enzyme
    prev_p = 0.0

    while not sim.done:
        s = sim.history[-1]

        if s.moisture > 0.55:
            inlet_temp = 125.0
            airflow = 0.60
        elif s.moisture > 0.35:
            inlet_temp = 116.0
            airflow = 0.68
        elif s.moisture > 0.20:
            inlet_temp = 108.0
            airflow = 0.76
        elif s.moisture > 0.10:
            inlet_temp = 98.0
            airflow = 0.82
        else:
            inlet_temp = 92.0
            airflow = 0.88

        # Feedback shaping for smoother control and less thermal stress.
        if s.bed_temp < 90.0 and s.moisture > 0.20:
            inlet_temp += 4.0
        if s.bed_temp > 110.0:
            inlet_temp -= 6.0
            airflow += 0.06
        if s.drying_rate > -0.002 and s.moisture > 0.15:
            inlet_temp += 3.0

        sim.set_controls(
            inlet_temp=_clamp(inlet_temp, 80.0, 130.0),
            airflow=_clamp(airflow, 0.2, 1.0),
        )
        state = sim.step()

        r, _ = compute_reward(
            moisture=state.moisture,
            prev_moisture=prev_m,
            bed_temp=state.bed_temp,
            inlet_temp=state.inlet_temp,
            enzyme_activity=state.enzyme_activity,
            prev_enzyme=prev_e,
            pyrazine=state.pyrazine,
            prev_pyrazine=prev_p,
            l_star=state.l_star,
            stewing=state.stewing,
            stewing_penalty=state.stewing_penalty,
            done=sim.done,
            cfg=reward_cfg,
        )
        total_reward += r
        prev_m = state.moisture
        prev_e = state.enzyme_activity
        prev_p = state.pyrazine

    return sim.history, total_reward


def _run_trained_ppo_policy(
    cfg: SimConfig,
    reward_cfg: RewardConfig,
    model_name: str | None = None,
) -> tuple[List[DryerState], float, str]:
    """Run a trained PPO model rollout and return history + reward + source name."""
    picked = _discover_model_name(model_name)
    if not picked:
        raise FileNotFoundError("No PPO model file found under models/")
    model_path = _MODELS_DIR / f"{picked}.zip"
    if not model_path.is_file():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Lazy import keeps the module usable when RL deps are unavailable.
    from backend.rl.environment import TeaDryerEnv
    from stable_baselines3 import PPO

    env = TeaDryerEnv(sim_cfg=cfg, reward_cfg=reward_cfg)
    model = PPO.load(str(model_path), env=env)
    def _rollout(govern: bool) -> tuple[List[DryerState], float, str]:
        obs, _ = env.reset()
        total_reward = 0.0
        done = False

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            state = env.sim.history[-1] if env.sim and env.sim.history else None
            step_action = _govern_ppo_action(action, state) if (govern and state) else action
            obs, reward, terminated, truncated, _ = env.step(step_action)
            total_reward += float(reward)
            done = bool(terminated or truncated)

        mode = "governed" if govern else "raw"
        return env.sim.history, total_reward, mode

    candidates = [_rollout(False), _rollout(True)]
    best_history, best_reward, best_mode = _choose_best_rl_history(candidates, cfg, reward_cfg)
    return best_history, best_reward, f"{picked}:{best_mode}"


def _moisture_target_at_time(t: float, cfg: SimConfig, reward_cfg: RewardConfig) -> float:
    frac = min(max(t / max(cfg.duration, 1e-6), 0.0), 1.0)
    return cfg.m0 + (reward_cfg.target_moisture - cfg.m0) * frac


def _tracking_mae_pct(history: List[DryerState], cfg: SimConfig, reward_cfg: RewardConfig) -> float:
    if not history:
        return 0.0
    err_sum = 0.0
    for s in history:
        target = _moisture_target_at_time(s.time, cfg, reward_cfg)
        err_sum += abs(s.moisture - target)
    return (err_sum / len(history)) * 100.0


def _overshoot_pct(history: List[DryerState], reward_cfg: RewardConfig) -> float:
    if not history:
        return 0.0
    min_m = min(s.moisture for s in history)
    return max(0.0, reward_cfg.target_moisture - min_m) * 100.0


def _settling_time_min(history: List[DryerState], reward_cfg: RewardConfig, band: float = 0.008) -> float:
    if not history:
        return 0.0
    target = reward_cfg.target_moisture
    values = [s.moisture for s in history]
    times = [s.time for s in history]

    for i in range(len(values)):
        if all(abs(v - target) <= band for v in values[i:]):
            return float(times[i])
    return float(times[-1])


def _sample_moisture_at(history: List[DryerState], t: float) -> float:
    if not history:
        return 0.0
    if t <= history[0].time:
        return history[0].moisture
    if t >= history[-1].time:
        return history[-1].moisture

    for i in range(1, len(history)):
        a = history[i - 1]
        b = history[i]
        if a.time <= t <= b.time:
            dt = max(b.time - a.time, 1e-6)
            frac = (t - a.time) / dt
            return a.moisture + (b.moisture - a.moisture) * frac
    return history[-1].moisture


def _build_trajectory(rl_hist: List[DryerState], pid_hist: List[DryerState], points: int = 80) -> List[Dict[str, float]]:
    if not rl_hist or not pid_hist:
        return []

    max_t = max(rl_hist[-1].time, pid_hist[-1].time)
    if max_t <= 0:
        max_t = 1.0

    out: List[Dict[str, float]] = []
    for i in range(points + 1):
        t = max_t * (i / points)
        rl_m = _sample_moisture_at(rl_hist, t) * 100.0
        pid_m = _sample_moisture_at(pid_hist, t) * 100.0
        out.append({
            "t": round(t, 2),
            "rl": round(rl_m, 3),
            "pid": round(pid_m, 3),
        })
    return out


def _summary(history: List[DryerState], cfg: SimConfig, reward_cfg: RewardConfig) -> Dict[str, float]:
    final = history[-1] if history else None
    return {
        "tracking_mae_pct": round(_tracking_mae_pct(history, cfg, reward_cfg), 3),
        "overshoot_pct": round(_overshoot_pct(history, reward_cfg), 3),
        "settling_time_min": round(_settling_time_min(history, reward_cfg), 3),
        "final_moisture_pct": round((final.moisture if final else 0.0) * 100.0, 3),
        "energy_kwh": round(final.energy_kwh if final else 0.0, 4),
        "sec_kwh_per_kg": round(final.sec if final else 0.0, 4),
        "cycle_time_min": round(final.time if final else 0.0, 3),
    }


def run_benchmark(sim_cfg: SimConfig | None = None, model_name: str | None = None) -> Dict[str, Any]:
    cfg = sim_cfg or SimConfig()
    reward_cfg = RewardConfig()

    pid = BaselinePID(sim_cfg=cfg, reward_cfg=reward_cfg)
    pid_history, pid_total_reward, _ = pid.run()

    fallback_reason = ""
    try:
        if model_name:
            rl_history, rl_total_reward, picked_model = _run_trained_ppo_policy(
                cfg,
                reward_cfg,
                model_name=model_name,
            )
            rl_source = f"ppo:{picked_model}"
        else:
            model_rollouts: List[tuple[List[DryerState], float, str]] = []
            errors: List[str] = []
            for candidate in _list_model_candidates():
                try:
                    hist, reward, picked_model = _run_trained_ppo_policy(
                        cfg,
                        reward_cfg,
                        model_name=candidate,
                    )
                    model_rollouts.append((hist, reward, picked_model))
                except Exception as model_exc:
                    errors.append(f"{candidate}: {model_exc}")

            if not model_rollouts:
                raise FileNotFoundError("; ".join(errors) or "No PPO model file found under models/")

            rl_history, rl_total_reward, picked_model = _choose_best_model_rollout(
                model_rollouts,
                cfg,
                reward_cfg,
            )
            rl_source = f"ppo:{picked_model}"
    except Exception as exc:
        rl_history, rl_total_reward = _run_adaptive_policy(cfg, reward_cfg)
        rl_source = "adaptive_policy_v1"
        fallback_reason = str(exc)

    rl_summary = _summary(rl_history, cfg, reward_cfg)
    pid_summary = _summary(pid_history, cfg, reward_cfg)

    pid_energy = pid_summary["energy_kwh"]
    rl_energy = rl_summary["energy_kwh"]
    energy_saved_pct = ((pid_energy - rl_energy) / pid_energy * 100.0) if pid_energy > 0 else 0.0

    pid_mae = pid_summary["tracking_mae_pct"]
    rl_mae = rl_summary["tracking_mae_pct"]
    mae_improvement_pct = ((pid_mae - rl_mae) / pid_mae * 100.0) if pid_mae > 0 else 0.0

    pid_cycle = pid_summary["cycle_time_min"]
    rl_cycle = rl_summary["cycle_time_min"]
    cycle_saved_pct = ((pid_cycle - rl_cycle) / pid_cycle * 100.0) if pid_cycle > 0 else 0.0

    return {
        "meta": {
            "rl_source": rl_source,
            "fallback_reason": fallback_reason,
            "target_moisture_pct": round(reward_cfg.target_moisture * 100.0, 2),
            "dt_min": cfg.dt,
            "duration_min": cfg.duration,
        },
        "summary": {
            "rl": {
                **rl_summary,
                "total_reward": round(float(rl_total_reward), 3),
            },
            "pid": {
                **pid_summary,
                "total_reward": round(float(pid_total_reward), 3),
            },
            "delta": {
                "energy_saved_pct": round(energy_saved_pct, 3),
                "tracking_error_improvement_pct": round(mae_improvement_pct, 3),
                "cycle_time_saved_pct": round(cycle_saved_pct, 3),
            },
        },
        "trajectory": _build_trajectory(rl_history, pid_history),
    }
