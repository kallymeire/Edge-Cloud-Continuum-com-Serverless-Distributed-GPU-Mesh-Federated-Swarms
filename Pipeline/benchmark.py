"""Benchmark for the scenario generator (CPU only, no rendering).

Measures how many episodes and frames per second the pipeline produces with a
different number of worker processes. Results depend on the machine, so run it
yourself and publish your own numbers.
"""
import argparse
import json
import os
import platform
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_simulation import _write_episode  # noqa: E402


def run(config, episodes, workers):
    with tempfile.TemporaryDirectory() as out:
        jobs = [(config, i, 0, out) for i in range(episodes)]
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_write_episode, jobs))
        return time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description="Scenario generator benchmark")
    parser.add_argument("--config", default="Pipeline/config.json")
    parser.add_argument("--episodes", type=int, default=2000)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8])
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    frames = config["frames_per_episode"]

    print(f"Machine: {platform.processor() or platform.machine()}, "
          f"{os.cpu_count()} logical CPUs, Python {platform.python_version()}")
    print(f"Episodes: {args.episodes}, frames per episode: {frames}\n")
    print("| Workers | Time (s) | Episodes/s | Frames/s |")
    print("| ---: | ---: | ---: | ---: |")
    for w in args.workers:
        t = run(config, args.episodes, w)
        print(f"| {w} | {t:.2f} | {args.episodes / t:.0f} | {args.episodes * frames / t:.0f} |")


if __name__ == "__main__":
    main()
