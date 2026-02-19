"""
train.py — Training & evaluation script for the AuraSense RL agent.

Usage
-----
    # Train PPO for 50k steps (quick demo)
    python -m backend.rl.train --algo PPO --steps 50000

    # Train SAC for 100k steps
    python -m backend.rl.train --algo SAC --steps 100000

    # Evaluate a saved model
    python -m backend.rl.train --eval --model tea_dryer_PPO

    # Compare RL vs PID
    python -m backend.rl.train --compare --model tea_dryer_PPO
"""

from __future__ import annotations

import argparse
import json
import sys

from backend.config import SimConfig
from backend.rl.agent import DryerAgent
from backend.rl.reward import RewardConfig


def train(args):
    print(f"\n🔧  Initialising {args.algo} agent...")
    agent = DryerAgent(
        algo=args.algo,
        sim_cfg=SimConfig(),
        reward_cfg=RewardConfig(),
    )

    agent.train(
        total_timesteps=args.steps,
        eval_freq=args.eval_freq,
        save_freq=args.save_freq,
        run_name=f"tea_dryer_{args.algo}",
    )

    # Save final model
    agent.save(f"tea_dryer_{args.algo}")

    # Quick evaluation
    print("\n📊  Post-training evaluation (5 episodes)...")
    results = agent.evaluate(n_episodes=5)
    print(json.dumps(results, indent=2))

    return agent


def evaluate(args):
    print(f"\n📊  Loading model: {args.model}")
    agent = DryerAgent.load(name=args.model, algo=args.algo)
    results = agent.evaluate(n_episodes=args.n_eval)
    print(json.dumps(results, indent=2))
    return results


def compare(args):
    print(f"\n⚔️   RL vs PID comparison  (model: {args.model})")
    agent = DryerAgent.load(name=args.model, algo=args.algo)
    results = agent.compare_with_pid(n_episodes=args.n_eval)

    print("\n" + "=" * 50)
    print(f"  RL  mean reward:   {results['rl']['mean_reward']:>8.2f}")
    print(f"  PID mean reward:   {results['pid']['mean_reward']:>8.2f}")
    print(f"  Improvement:       {results['reward_improvement']:>+8.2f}  "
          f"({results['improvement_pct']:>+.1f}%)")
    print(
        f"  RL  final M:       {results['rl']['mean_final_moisture']*100:.1f}%")
    print(
        f"  PID final M:       {results['pid']['mean_final_moisture']*100:.1f}%")
    print("=" * 50)

    return results


def main():
    parser = argparse.ArgumentParser(description="AuraSense RL Training")
    parser.add_argument("--algo", choices=["PPO", "SAC"], default="PPO",
                        help="RL algorithm (default: PPO)")
    parser.add_argument("--steps", type=int, default=50_000,
                        help="Total training timesteps (default: 50000)")
    parser.add_argument("--eval-freq", type=int, default=5_000,
                        help="Evaluate every N steps (default: 5000)")
    parser.add_argument("--save-freq", type=int, default=10_000,
                        help="Checkpoint every N steps (default: 10000)")
    parser.add_argument("--eval", action="store_true",
                        help="Evaluate a saved model instead of training")
    parser.add_argument("--compare", action="store_true",
                        help="Compare RL vs PID")
    parser.add_argument("--model", type=str, default="tea_dryer_PPO",
                        help="Model name for eval/compare (default: tea_dryer_PPO)")
    parser.add_argument("--n-eval", type=int, default=5,
                        help="Number of evaluation episodes (default: 5)")

    args = parser.parse_args()

    if args.eval:
        evaluate(args)
    elif args.compare:
        compare(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
