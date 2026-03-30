"""
agent.py — RL agent wrapper (PPO / SAC) for the tea dryer.

Provides a clean interface for:
    • Training a new agent
    • Loading a pre-trained agent
    • Running inference (single episode)
    • Comparing RL vs PID performance

Uses Stable-Baselines3 under the hood.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import numpy as np
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.callbacks import (
    BaseCallback,
    EvalCallback,
    CheckpointCallback,
)
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from backend.config import SimConfig
from backend.rl.environment import TeaDryerEnv
from backend.rl.reward import RewardConfig
from backend.rl.baseline_pid import BaselinePID


# ─── Default paths ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = _PROJECT_ROOT / "models"
LOGS_DIR = _PROJECT_ROOT / "logs"


# ─── Custom callback for episode logging ─────────────────

class EpisodeLogCallback(BaseCallback):
    """Logs episode-level metrics to stdout during training."""

    def __init__(self, verbose: int = 1):
        super().__init__(verbose)
        self._episode_count = 0

    def _on_step(self) -> bool:
        # Check if any env just finished an episode
        for info in self.locals.get("infos", []):
            if "episode" in info:
                self._episode_count += 1
                ep = info["episode"]
                if self.verbose >= 1 and self._episode_count % 10 == 0:
                    print(
                        f"  Episode {self._episode_count:>4d}  "
                        f"R={ep['r']:>7.2f}  "
                        f"len={ep['l']:>4d}  "
                        f"M={info.get('moisture', '?')}"
                    )
        return True


# ─── Agent class ──────────────────────────────────────────

class DryerAgent:
    """
    High-level RL agent for the tea dryer environment.

    Usage
    -----
        agent = DryerAgent(algo="PPO")
        agent.train(total_timesteps=50_000)
        agent.save("my_model")

        # Later:
        agent = DryerAgent.load("my_model")
        result = agent.evaluate()
    """

    ALGOS = {"PPO": PPO, "SAC": SAC}

    def __init__(
        self,
        algo: Literal["PPO", "SAC"] = "PPO",
        sim_cfg: SimConfig | None = None,
        reward_cfg: RewardConfig | None = None,
        model_kwargs: dict | None = None,
    ):
        self.algo_name = algo
        self.sim_cfg = sim_cfg or SimConfig()
        self.reward_cfg = reward_cfg or RewardConfig()

        self.env = self._make_env()
        self.eval_env = self._make_env()

        # Default hyperparameters tuned for this problem
        defaults = self._default_hyperparams(algo)
        if model_kwargs:
            defaults.update(model_kwargs)

        algo_cls = self.ALGOS[algo]
        self.model = algo_cls(
            policy="MlpPolicy",
            env=self.env,
            verbose=1,
            tensorboard_log=str(LOGS_DIR),
            **defaults,
        )

    def _make_env(self):
        """Create a monitored vectorised env."""
        def _env_fn():
            env = TeaDryerEnv(
                sim_cfg=self.sim_cfg,
                reward_cfg=self.reward_cfg,
            )
            return Monitor(env)
        return DummyVecEnv([_env_fn])

    @staticmethod
    def _default_hyperparams(algo: str) -> dict:
        if algo == "PPO":
            return {
                "learning_rate": 3e-4,
                "n_steps": 300,          # ~1 full episode per rollout
                "batch_size": 60,        # factor of 300
                "n_epochs": 10,
                "gamma": 0.99,
                "gae_lambda": 0.95,
                "clip_range": 0.2,
                "ent_coef": 0.01,        # encourage exploration
                "policy_kwargs": {"net_arch": [128, 128]},
            }
        elif algo == "SAC":
            return {
                "learning_rate": 3e-4,
                "buffer_size": 50_000,
                "batch_size": 128,
                "gamma": 0.99,
                "tau": 0.005,
                "ent_coef": "auto",
                "policy_kwargs": {"net_arch": [128, 128]},
            }
        return {}

    # ─── Training ─────────────────────────────────────────

    def train(
        self,
        total_timesteps: int = 50_000,
        eval_freq: int = 5_000,
        save_freq: int = 10_000,
        run_name: str | None = None,
    ) -> None:
        """
        Train the agent.

        Parameters
        ----------
        total_timesteps : int    Total environment steps.
        eval_freq : int          Evaluate every N steps.
        save_freq : int          Checkpoint every N steps.
        run_name : str           Name for TensorBoard run & checkpoints.
        """
        name = run_name or f"tea_dryer_{self.algo_name}"
        ckpt_dir = MODELS_DIR / name / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        callbacks = [
            EpisodeLogCallback(verbose=1),
            EvalCallback(
                self.eval_env,
                best_model_save_path=str(MODELS_DIR / name),
                log_path=str(LOGS_DIR / name),
                eval_freq=eval_freq,
                n_eval_episodes=5,
                deterministic=True,
                verbose=1,
            ),
            CheckpointCallback(
                save_freq=save_freq,
                save_path=str(ckpt_dir),
                name_prefix=name,
                verbose=1,
            ),
        ]

        print(f"\n{'='*60}")
        print(
            f"  Training {self.algo_name} agent  |  {total_timesteps:,} steps")
        print(f"  Checkpoints → {ckpt_dir}")
        print(f"  TensorBoard → {LOGS_DIR / name}")
        print(f"{'='*60}\n")

        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            tb_log_name=name,
            progress_bar=True,
        )

    # ─── Save / Load ─────────────────────────────────────

    def save(self, name: str = "tea_dryer_best") -> Path:
        """Save model weights."""
        path = MODELS_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(str(path))
        print(f"Model saved → {path}")
        return path

    @classmethod
    def load(
        cls,
        name: str = "tea_dryer_best",
        algo: Literal["PPO", "SAC"] = "PPO",
        sim_cfg: SimConfig | None = None,
        reward_cfg: RewardConfig | None = None,
    ) -> "DryerAgent":
        """Load a pre-trained model."""
        instance = cls.__new__(cls)
        instance.algo_name = algo
        instance.sim_cfg = sim_cfg or SimConfig()
        instance.reward_cfg = reward_cfg or RewardConfig()
        instance.env = instance._make_env()
        instance.eval_env = instance._make_env()

        path = MODELS_DIR / name
        zip_path = MODELS_DIR / f"{name}.zip"
        if zip_path.is_file():
            path = zip_path
        algo_cls = cls.ALGOS[algo]
        instance.model = algo_cls.load(str(path), env=instance.env)
        print(f"Model loaded ← {path}")
        return instance

    # ─── Evaluation ───────────────────────────────────────

    def evaluate(self, n_episodes: int = 1, render: bool = False) -> dict:
        """
        Run the trained agent for n_episodes and return metrics.
        """
        rewards = []
        final_moistures = []
        final_pyrazines = []
        stewing_flags = []

        for ep in range(n_episodes):
            reset_out = self.eval_env.reset()
            obs = reset_out[0] if isinstance(reset_out, tuple) else reset_out
            done = False
            ep_reward = 0.0

            while not done:
                action, _ = self.model.predict(obs, deterministic=True)
                step_out = self.eval_env.step(action)

                # SB3 VecEnv commonly returns (obs, rewards, dones, infos),
                # while some envs return Gymnasium-style 5-tuples.
                if len(step_out) == 5:
                    obs, reward, terminated, truncated, info = step_out
                    dones = np.logical_or(terminated, truncated)
                else:
                    obs, reward, dones, info = step_out

                reward_arr = np.asarray(reward).reshape(-1)
                done_arr = np.asarray(dones).reshape(-1)
                ep_reward += float(reward_arr[0])
                done = bool(done_arr[0])
                if render:
                    self.eval_env.render()

            # Extract final info from the inner env
            inner_env = self.eval_env.envs[0].unwrapped
            last_state = inner_env.sim.history[-1]
            rewards.append(ep_reward)
            final_moistures.append(last_state.moisture)
            final_pyrazines.append(last_state.pyrazine)
            stewing_flags.append(last_state.stewing_penalty)

        return {
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "mean_final_moisture": float(np.mean(final_moistures)),
            "mean_final_pyrazine": float(np.mean(final_pyrazines)),
            "stewing_rate": float(np.mean(stewing_flags)),
            "n_episodes": n_episodes,
        }

    # ─── Comparison ───────────────────────────────────────

    def compare_with_pid(self, n_episodes: int = 5) -> dict:
        """
        Run both RL agent and PID baseline for n_episodes and compare.
        """
        rl_results = self.evaluate(n_episodes=n_episodes)

        pid = BaselinePID(
            sim_cfg=self.sim_cfg,
            reward_cfg=self.reward_cfg,
        )
        pid_env = TeaDryerEnv(sim_cfg=self.sim_cfg, reward_cfg=self.reward_cfg)

        pid_rewards = []
        pid_moistures = []
        pid_pyrazines = []
        for _ in range(n_episodes):
            r, infos = pid.run_in_env(pid_env)
            pid_rewards.append(r)
            last = pid_env.sim.history[-1]
            pid_moistures.append(last.moisture)
            pid_pyrazines.append(last.pyrazine)

        pid_results = {
            "mean_reward": float(np.mean(pid_rewards)),
            "std_reward": float(np.std(pid_rewards)),
            "mean_final_moisture": float(np.mean(pid_moistures)),
            "mean_final_pyrazine": float(np.mean(pid_pyrazines)),
        }

        improvement = rl_results["mean_reward"] - pid_results["mean_reward"]

        return {
            "rl": rl_results,
            "pid": pid_results,
            "reward_improvement": improvement,
            "improvement_pct": (
                improvement / abs(pid_results["mean_reward"]) * 100
                if pid_results["mean_reward"] != 0 else 0
            ),
        }
