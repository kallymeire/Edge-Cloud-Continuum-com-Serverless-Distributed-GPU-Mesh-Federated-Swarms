"""Scenario generation CLI.

Generates domain-randomized episodes in parallel and writes one JSON file per
episode. Rendering inside O3DE is not wired up yet: this step produces the
scenario descriptions that the simulator will consume.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.domain_randomizer import generate_episode  # noqa: E402


def _write_episode(args):
    config, episode_id, seed, output_dir = args
    episode = generate_episode(config, episode_id, seed)
    path = os.path.join(output_dir, f"episode_{episode_id:05d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(episode, f, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description="Domain-randomized scenario generator")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--output-dir", required=True, help="Where to write episode JSON files")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker processes")
    parser.add_argument("--seed", type=int, default=0, help="Base random seed")
    parser.add_argument("--episodes", type=int, help="Override episode count from config")
    parser.add_argument("--enable-llm-agents", action="store_true",
                        help="Reserved: LLM bridge is not implemented yet")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    episodes = args.episodes or config["episodes"]

    if args.enable_llm_agents:
        print("[WARN] --enable-llm-agents: LLM bridge not implemented yet, ignoring.")

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"[INIT] {episodes} episodes, {args.workers} workers, seed={args.seed}")

    jobs = [(config, i, args.seed, args.output_dir) for i in range(episodes)]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        paths = list(pool.map(_write_episode, jobs))
    elapsed = time.perf_counter() - start

    print(f"[DONE] {len(paths)} episodes written to {args.output_dir} in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
