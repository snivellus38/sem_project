"""
environment.py — Gymnasium environment wrapping the FBD physics engine.

Observation space  (19 floats)
------------------------------
    [0]       moisture           (wet-basis fraction)
    [1]       bed_temp           (°C, /150 normalised)
    [2]       inlet_temp         (°C, /150 normalised)
    [3]       enzyme_activity    (0–1)
    [4]       pyrazine           (µg/g, /5 normalised)
    [5]       l_star             (/60 normalised)
    [6]       a_star             (/20 normalised, shifted)
    [7]       b_star             (/30 normalised)
    [8]       drying_rate        (fraction/min, clipped & scaled)
    [9]       elapsed_frac       (t / duration)
    [10]      stewing_flag       (0 or 1)
    [11–18]   e-nose 8 voltages  (/4.5 normalised)

Action space  (2 continuous floats, clipped to [-1, 1])
-------------------------------------------------------
    [0]  inlet_temp_delta   mapped to [80, 130] °C
    [1]  airflow_damper     mapped to [0.2, 1.0]

Episode
-------
One episode = one full drying batch (≤ duration minutes or until target
moisture is reached).
"""

from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from backend.config import SimConfig
from backend.simulation.dryer import FBDSimulation
from backend.rl.reward import compute_reward, RewardConfig


class TeaDryerEnv(gym.Env):
    """OpenAI Gymnasium environment for the Fluidized Bed Dryer."""

    metadata = {"render_modes": ["human"], "render_fps": 10}

    def __init__(
        self,
        sim_cfg: SimConfig | None = None,
        reward_cfg: RewardConfig | None = None,
        render_mode: str | None = None,
    ):
        super().__init__()
        self.sim_cfg = sim_cfg or SimConfig()
        self.reward_cfg = reward_cfg or RewardConfig()
        self.render_mode = render_mode

        # ── Observation space: 19 floats, all normalised to ~[0, 1] ──
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(19,), dtype=np.float32,
        )

        # ── Action space: 2 continuous [-1, 1] ──
        # Mapped in step() to physical ranges
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(2,), dtype=np.float32,
        )

        self.sim: FBDSimulation | None = None
        self._prev_moisture = self.sim_cfg.m0
        self._prev_enzyme = self.sim_cfg.c0_enzyme
        self._prev_pyrazine = 0.0
        self._episode_reward = 0.0
        self._step_count = 0

    # ─── Gymnasium API ────────────────────────────────────

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.sim = FBDSimulation(self.sim_cfg)
        self._prev_moisture = self.sim_cfg.m0
        self._prev_enzyme = self.sim_cfg.c0_enzyme
        self._prev_pyrazine = 0.0
        self._episode_reward = 0.0
        self._step_count = 0
        obs = self._get_obs()
        info = self._get_info()
        return obs, info

    def step(self, action: np.ndarray):
        assert self.sim is not None, "Call reset() before step()"

        # ── Map actions to physical controls ──────────────
        # action[0] ∈ [-1, 1] → inlet_temp ∈ [80, 130] °C
        inlet_temp = float(np.clip(action[0], -1, 1)) * 25.0 + 105.0
        # action[1] ∈ [-1, 1] → airflow ∈ [0.2, 1.0]
        airflow = float(np.clip(action[1], -1, 1)) * 0.4 + 0.6

        self.sim.set_controls(inlet_temp=inlet_temp, airflow=airflow)
        state = self.sim.step()
        self._step_count += 1

        # ── Reward ────────────────────────────────────────
        reward, reward_info = compute_reward(
            moisture=state.moisture,
            prev_moisture=self._prev_moisture,
            bed_temp=state.bed_temp,
            inlet_temp=state.inlet_temp,
            enzyme_activity=state.enzyme_activity,
            prev_enzyme=self._prev_enzyme,
            pyrazine=state.pyrazine,
            prev_pyrazine=self._prev_pyrazine,
            l_star=state.l_star,
            stewing=state.stewing,
            stewing_penalty=state.stewing_penalty,
            done=self.sim.done,
            cfg=self.reward_cfg,
        )

        self._prev_moisture = state.moisture
        self._prev_enzyme = state.enzyme_activity
        self._prev_pyrazine = state.pyrazine
        self._episode_reward += reward

        # ── Termination ───────────────────────────────────
        terminated = self.sim.done
        truncated = False       # no time-limit truncation (sim handles it)

        obs = self._get_obs()
        info = self._get_info()
        info["reward_breakdown"] = reward_info

        return obs, float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode == "human" and self.sim is not None:
            s = self.sim.history[-1]
            print(
                f"t={s.time:5.1f}  M={s.moisture*100:5.1f}%  "
                f"T_bed={s.bed_temp:5.1f}°C  T_in={s.inlet_temp:5.1f}°C  "
                f"Enz={s.enzyme_activity:.3f}  Pyr={s.pyrazine:.2f}  "
                f"L*={s.l_star:.1f}  {s.color_hex}  "
                f"R={self._episode_reward:.2f}"
            )

    # ─── Internal helpers ─────────────────────────────────

    def _get_obs(self) -> np.ndarray:
        """Build the normalised observation vector."""
        if self.sim is None or len(self.sim.history) == 0:
            return np.zeros(19, dtype=np.float32)

        s = self.sim.history[-1]

        # E-nose voltages (8 channels, normalised to [0, 1])
        if s.sensors is not None:
            enose = [v / 4.5 for v in s.sensors.enose.voltages]
        else:
            enose = [0.0] * 8

        obs = np.array([
            s.moisture,                                  # [0]
            s.bed_temp / 150.0,                          # [1]
            s.inlet_temp / 150.0,                        # [2]
            s.enzyme_activity,                           # [3]
            min(s.pyrazine / 5.0, 1.0),                  # [4]
            s.l_star / 60.0,                             # [5]
            # [6] shift a* to positive
            (s.a_star + 10.0) / 25.0,
            s.b_star / 30.0,                             # [7]
            np.clip(s.drying_rate * -50.0, 0, 1),        # [8] positive, scaled
            s.time / self.sim_cfg.duration,              # [9]
            1.0 if s.stewing else 0.0,                   # [10]
            *enose,                                      # [11–18]
        ], dtype=np.float32)

        return np.clip(obs, 0.0, 1.0)

    def _get_info(self) -> dict:
        """Extra info for logging."""
        if self.sim is None or len(self.sim.history) == 0:
            return {}
        s = self.sim.history[-1]
        return {
            "time": s.time,
            "moisture": s.moisture,
            "bed_temp": s.bed_temp,
            "enzyme_activity": s.enzyme_activity,
            "pyrazine": s.pyrazine,
            "episode_reward": self._episode_reward,
            "steps": self._step_count,
            "color_hex": s.color_hex,
        }
