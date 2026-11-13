"""Benchmark for the federated aggregation prototype.

Sweeps the top-k fraction (share of delta-w entries sent each round) and
reports, averaged over several seeds:
  * final test accuracy of the federated model and its gap to centralized training
  * total bytes sent as delta-w, and the reduction versus dense float32 deltas
    and versus shipping all raw samples to one place

Uses the synthetic logistic-regression setup in core/federated_aggregator.py,
so numbers describe that setup, not a real robotics workload.
"""
import argparse
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.federated_aggregator import run  # noqa: E402


def mean_std(values):
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def main():
    parser = argparse.ArgumentParser(description="Federated traffic benchmark")
    parser.add_argument("--topk", type=float, nargs="+", default=[1.0, 0.5, 0.25, 0.1, 0.05, 0.02])
    parser.add_argument("--seeds", type=int, default=5, help="number of seeds to average")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--samples", type=int, default=500)
    args = parser.parse_args()

    print(f"Setup: {args.workers} workers, {args.rounds} rounds, dim={args.dim}, "
          f"{args.samples} samples/worker, {args.seeds} seeds\n")
    print("| Top-k | Federated acc | Gap vs centralized | Sent (KiB) | vs dense float32 | vs raw data |")
    print("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for k in args.topk:
        runs = [
            run(workers=args.workers, rounds=args.rounds, dim=args.dim,
                samples=args.samples, topk=k, seed=s).summary
            for s in range(args.seeds)
        ]
        acc, acc_sd = mean_std([r["federated_acc"] for r in runs])
        gap, gap_sd = mean_std([r["acc_gap"] for r in runs])
        kib = statistics.mean(r["bytes_delta_w_total"] for r in runs) / 1024
        dense = statistics.mean(r["traffic_reduction_vs_dense"] for r in runs)
        raw = statistics.mean(r["traffic_reduction_vs_raw"] for r in runs)
        print(f"| {k:g} | {acc:.3f} ± {acc_sd:.3f} | {gap:+.3f} ± {gap_sd:.3f} | "
              f"{kib:.1f} | {dense:.1f}x | {raw:.1f}x |")


if __name__ == "__main__":
    main()
