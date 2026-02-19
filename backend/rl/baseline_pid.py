"""
baseline_pid.py — Classic PID controller for the tea dryer.

Serves as the benchmark that the RL agent must beat.  A real-world FBD
typically uses a simple PID loop on exhaust temperature or outlet moisture.

We implement two cascaded PIDs:
    1. **Moisture PID** — adjusts inlet temperature to track a moisture
       setpoint trajectory (linear ramp from M0 → target over the cycle).
    2. **Temperature PID** — adjusts airflow to keep bed temperature
       stable (secondary loop, prevents overshoot).

The PID outputs are clipped to safe physical ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from backend.config import SimConfig
from backend.simulation.dryer import FBDSimulation, DryerState
from backend.rl.reward import compute_reward, RewardConfig


@dataclass
class PIDGains:
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.05


class PIDController:
    """Simple discrete PID with anti-windup clamp."""

    def __init__(self, gains: PIDGains, out_min: float, out_max: float):
        self.kp = gains.kp
        self.ki = gains.ki
        self.kd = gains.kd
        self.out_min = out_min
        self.out_max = out_max
        self._integral = 0.0
        self._prev_error = 0.0

    def update(self, error: float, dt: float) -> float:
        self._integral += error * dt
        # Anti-windup: clamp integral so output stays in bounds
        self._integral = np.clip(
            self._integral,
            (self.out_min - self.kp * error) / max(self.ki, 1e-6),
            (self.out_max - self.kp * error) / max(self.ki, 1e-6),
        )
        derivative = (error - self._prev_error) / max(dt, 1e-6)
        self._prev_error = error
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return float(np.clip(output, self.out_min, self.out_max))

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


class BaselinePID:
    """
    Two-loop PID controller for the FBD.

    Usage
    -----
        pid = BaselinePID()
        result = pid.run()          # returns (history, total_reward, reward_log)
        pid.run_in_env(env)        # run inside the Gymnasium env for comparison
    """

    def __init__(
        self,
        sim_cfg: SimConfig | None = None,
        reward_cfg: RewardConfig | None = None,
        moisture_gains: PIDGains | None = None,
        temp_gains: PIDGains | None = None,
    ):
        self.sim_cfg = sim_cfg or SimConfig()
        self.reward_cfg = reward_cfg or RewardConfig()

        # Moisture PID: error → inlet temperature adjustment
        # Positive error (moisture too high) → raise temp
        m_gains = moisture_gains or PIDGains(kp=300.0, ki=15.0, kd=20.0)
        self.moisture_pid = PIDController(m_gains, out_min=80.0, out_max=130.0)

        # Temperature PID: error → airflow adjustment
        # Positive error (bed too hot) → increase airflow
        t_gains = temp_gains or PIDGains(kp=0.02, ki=0.005, kd=0.002)
        self.temp_pid = PIDController(t_gains, out_min=0.2, out_max=1.0)

    def _moisture_setpoint(self, t: float) -> float:
        """
        Linear ramp from initial moisture to target over the cycle duration.
        """
        cfg = self.sim_cfg
        target = self.reward_cfg.target_moisture
        frac = min(t / cfg.duration, 1.0)
        return cfg.m0 + (target - cfg.m0) * frac

    def _temp_setpoint(self, t: float) -> float:
        """
        Temperature profile: start moderate, ramp up mid-cycle for Maillard.
        """
        frac = min(t / self.sim_cfg.duration, 1.0)
        if frac < 0.7:
            return 100.0        # steady drying phase
        else:
            # Ramp to 115 °C in final 30% for flavour development
            return 100.0 + (frac - 0.7) / 0.3 * 15.0

    def run(self):
        """
        Run the full drying cycle under PID control.

        Returns
        -------
        history : list[DryerState]
        total_reward : float
        reward_log : list[dict]
        """
        sim = FBDSimulation(self.sim_cfg)
        dt = self.sim_cfg.dt

        self.moisture_pid.reset()
        self.temp_pid.reset()

        total_reward = 0.0
        reward_log = []

        prev_moisture = self.sim_cfg.m0
        prev_enzyme = self.sim_cfg.c0_enzyme
        prev_pyrazine = 0.0

        while not sim.done:
            s = sim.history[-1]

            # Moisture PID → inlet temperature
            m_sp = self._moisture_setpoint(s.time)
            m_err = s.moisture - m_sp               # positive = too wet → more heat
            inlet_temp = self.moisture_pid.update(m_err, dt)

            # Temperature PID → airflow
            t_sp = self._temp_setpoint(s.time)
            t_err = s.bed_temp - t_sp               # positive = too hot → more air
            airflow = self.temp_pid.update(t_err, dt)

            sim.set_controls(inlet_temp=inlet_temp, airflow=airflow)
            state = sim.step()

            # Compute reward for fair comparison with RL
            r, r_info = compute_reward(
                moisture=state.moisture,
                prev_moisture=prev_moisture,
                bed_temp=state.bed_temp,
                inlet_temp=state.inlet_temp,
                enzyme_activity=state.enzyme_activity,
                prev_enzyme=prev_enzyme,
                pyrazine=state.pyrazine,
                prev_pyrazine=prev_pyrazine,
                l_star=state.l_star,
                stewing=state.stewing,
                stewing_penalty=state.stewing_penalty,
                done=sim.done,
                cfg=self.reward_cfg,
            )
            total_reward += r
            reward_log.append(r_info)

            prev_moisture = state.moisture
            prev_enzyme = state.enzyme_activity
            prev_pyrazine = state.pyrazine

        return sim.history, total_reward, reward_log

    def run_in_env(self, env):
        """
        Run the PID controller inside a Gymnasium env (for apples-to-apples
        comparison with the RL agent).

        Returns (total_reward, info_list).
        """
        obs, info = env.reset()
        self.moisture_pid.reset()
        self.temp_pid.reset()
        dt = self.sim_cfg.dt

        total_reward = 0.0
        infos = [info]

        done = False
        while not done:
            # Read state from the env's sim
            s = env.sim.history[-1]

            m_sp = self._moisture_setpoint(s.time)
            m_err = s.moisture - m_sp
            inlet_temp = self.moisture_pid.update(m_err, dt)

            t_sp = self._temp_setpoint(s.time)
            t_err = s.bed_temp - t_sp
            airflow = self.temp_pid.update(t_err, dt)

            # Convert physical controls → action space [-1, 1]
            action = np.array([
                (inlet_temp - 105.0) / 25.0,
                (airflow - 0.6) / 0.4,
            ], dtype=np.float32)
            action = np.clip(action, -1.0, 1.0)

            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            infos.append(info)
            done = terminated or truncated

        return total_reward, infos
