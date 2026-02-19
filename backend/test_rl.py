"""
test_rl.py — Phase 4 tests: Gymnasium env, reward, PID baseline, RL agent.

Run:  python -m backend.test_rl
"""

from __future__ import annotations

import numpy as np

from backend.config import SimConfig
from backend.rl.environment import TeaDryerEnv
from backend.rl.reward import compute_reward, RewardConfig
from backend.rl.baseline_pid import BaselinePID


def test_env_creation():
    env = TeaDryerEnv()
    assert env.observation_space.shape == (19,)
    assert env.action_space.shape == (2,)
    print("[PASS] env_creation  (obs=19, act=2)")


def test_env_reset():
    env = TeaDryerEnv()
    obs, info = env.reset()
    assert obs.shape == (19,)
    assert obs.dtype == np.float32
    assert 0.0 <= obs.min() and obs.max(
    ) <= 1.0, f"Obs out of [0,1]: {obs.min():.3f}–{obs.max():.3f}"
    assert info["moisture"] > 0.6
    print(f"[PASS] env_reset  (M={info['moisture']*100:.1f}%)")


def test_env_step():
    env = TeaDryerEnv()
    env.reset()

    # Neutral action
    action = np.array([0.0, 0.0], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    assert obs.shape == (19,)
    assert isinstance(reward, float)
    assert not truncated
    assert "reward_breakdown" in info
    print(f"[PASS] env_step  (reward={reward:.4f})")


def test_env_full_episode():
    env = TeaDryerEnv()
    obs, _ = env.reset()

    total_reward = 0.0
    steps = 0

    while True:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1
        if terminated or truncated:
            break

    assert steps > 50, f"Episode too short: {steps} steps"
    print(f"[PASS] env_full_episode  (steps={steps}, R={total_reward:.2f}, "
          f"M={info['moisture']*100:.1f}%)")


def test_reward_positive_drying():
    """Drying progress should give positive reward."""
    r, info = compute_reward(
        moisture=0.50, prev_moisture=0.55,
        bed_temp=95.0, inlet_temp=100.0,
        enzyme_activity=0.5, prev_enzyme=0.6,
        pyrazine=0.0, prev_pyrazine=0.0,
        l_star=40.0, stewing=False, stewing_penalty=False,
        done=False,
    )
    assert info["drying"] > 0, f"Drying reward should be positive: {info['drying']}"
    assert info["enzyme"] > 0, f"Enzyme reward should be positive: {info['enzyme']}"
    print(
        f"[PASS] reward_positive_drying  (drying={info['drying']:.3f}, enz={info['enzyme']:.3f})")


def test_reward_stewing_penalty():
    """Stewing should produce a large negative reward."""
    r, info = compute_reward(
        moisture=0.60, prev_moisture=0.60,
        bed_temp=50.0, inlet_temp=55.0,
        enzyme_activity=0.9, prev_enzyme=0.9,
        pyrazine=0.0, prev_pyrazine=0.0,
        l_star=50.0, stewing=True, stewing_penalty=True,
        done=False,
    )
    assert info["stewing"] < - \
        5.0, f"Stewing penalty too weak: {info['stewing']}"
    print(f"[PASS] reward_stewing_penalty  (stew={info['stewing']:.2f})")


def test_reward_terminal_bonus():
    """Hitting target moisture at end should give a terminal bonus."""
    r, info = compute_reward(
        moisture=0.04, prev_moisture=0.045,
        bed_temp=100.0, inlet_temp=100.0,
        enzyme_activity=0.0, prev_enzyme=0.0,
        pyrazine=0.5, prev_pyrazine=0.5,
        l_star=25.0, stewing=False, stewing_penalty=False,
        done=True,
    )
    assert info["terminal"] > 5.0, f"Terminal bonus too low: {info['terminal']}"
    print(f"[PASS] reward_terminal_bonus  (terminal={info['terminal']:.2f})")


def test_pid_baseline():
    """PID controller should produce a valid drying trajectory."""
    pid = BaselinePID()
    history, total_reward, reward_log = pid.run()

    last = history[-1]
    assert last.moisture < 0.08, f"PID: final moisture too high: {last.moisture}"
    assert last.enzyme_activity < 0.01, "PID: enzyme should be dead"
    assert len(reward_log) > 100, f"PID: too few steps: {len(reward_log)}"

    print(f"[PASS] pid_baseline  (M={last.moisture*100:.1f}%, "
          f"R={total_reward:.2f}, steps={len(reward_log)})")


def test_pid_in_env():
    """PID running inside the Gymnasium env should match standalone."""
    env = TeaDryerEnv()
    pid = BaselinePID()
    total_reward, infos = pid.run_in_env(env)

    last_info = infos[-1]
    assert last_info["moisture"] < 0.08
    print(f"[PASS] pid_in_env  (R={total_reward:.2f}, "
          f"M={last_info['moisture']*100:.1f}%)")


def test_rl_quick_train():
    """Smoke test: train PPO for 600 steps (2 episodes) and verify it runs."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.monitor import Monitor

    def make_env():
        return Monitor(TeaDryerEnv())

    env = DummyVecEnv([make_env])
    model = PPO(
        "MlpPolicy", env,
        n_steps=300,
        batch_size=64,
        n_epochs=3,
        verbose=0,
        policy_kwargs={"net_arch": [64, 64]},
    )
    model.learn(total_timesteps=600)

    # Run one deterministic episode
    obs = env.reset()
    done = False
    ep_reward = 0.0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done_arr, _ = env.step(action)
        ep_reward += float(reward[0])
        done = done_arr[0]

    print(f"[PASS] rl_quick_train  (600 steps, eval R={ep_reward:.2f})")


if __name__ == "__main__":
    test_env_creation()
    test_env_reset()
    test_env_step()
    test_env_full_episode()
    test_reward_positive_drying()
    test_reward_stewing_penalty()
    test_reward_terminal_bonus()
    test_pid_baseline()
    test_pid_in_env()
    test_rl_quick_train()
    print("\n✅ All Phase 4 RL tests passed.")
