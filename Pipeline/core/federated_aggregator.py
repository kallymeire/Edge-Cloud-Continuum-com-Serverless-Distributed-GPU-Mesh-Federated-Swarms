"""Federated aggregation prototype for the Edge-Cloud Continuum.

Simulation workers train locally and ship only compressed weight deltas
(delta-w) to an aggregator. Raw samples never leave the worker. This module is
a self-contained reference: it needs only NumPy and runs on a laptop.

What it models
--------------
* Workers: each one owns a shard of data drawn from its own randomized domain
  (feature shift and scale), standing in for per-episode domain randomization.
* Update path: delta-w = w_local - w_global, then top-k sparsification with
  error feedback, then int8 quantization. Byte counts are computed from the
  actual wire format (indices + int8 values + one float32 scale).
* Aggregator: sample-weighted FedAvg over the decompressed deltas.
* Baselines: centralized training on pooled data (accuracy reference) and the
  bytes needed to ship all raw samples to one place (traffic reference).

The model is logistic regression. It is deliberately small so the result is
easy to reproduce and to check; the communication pattern is what the project
cares about, and it carries over to larger models.

Usage
-----
    python Pipeline/core/federated_aggregator.py --workers 8 --rounds 30
    python Pipeline/core/federated_aggregator.py --topk 0.05 --output fed.json
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

FLOAT_BYTES = 4  # wire format uses float32 for dense payloads
SCALE_BYTES = 4  # one float32 scale per compressed message


# --------------------------------------------------------------------------
# Data: one randomized domain per worker
# --------------------------------------------------------------------------
@dataclass
class Shard:
    x: np.ndarray  # (n, d + 1), last column is the constant bias feature
    y: np.ndarray  # (n,) in {0, 1}


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def make_domain_data(
    n: int, w_true: np.ndarray, rng: np.random.Generator, shift: float, scale_range: Tuple[float, float]
) -> Shard:
    """Sample one worker's data from a randomized domain.

    `shift` moves the feature mean and `scale_range` stretches it, the same
    kind of perturbation the domain randomizer applies to a simulation.
    """
    d = w_true.shape[0] - 1
    mu = rng.normal(0.0, shift, size=d)
    scale = rng.uniform(*scale_range)
    feats = mu + scale * rng.normal(size=(n, d))
    x = np.hstack([feats, np.ones((n, 1))])
    y = (rng.random(n) < _sigmoid(x @ w_true)).astype(np.float64)
    return Shard(x=x, y=y)


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------
def loss_and_acc(w: np.ndarray, shard: Shard) -> Tuple[float, float]:
    p = np.clip(_sigmoid(shard.x @ w), 1e-9, 1 - 1e-9)
    loss = -np.mean(shard.y * np.log(p) + (1 - shard.y) * np.log(1 - p))
    acc = np.mean((p >= 0.5) == (shard.y >= 0.5))
    return float(loss), float(acc)


def local_sgd(
    w: np.ndarray, shard: Shard, steps: int, lr: float, batch: int, l2: float, rng: np.random.Generator
) -> np.ndarray:
    w = w.copy()
    n = shard.x.shape[0]
    for _ in range(steps):
        idx = rng.integers(0, n, size=min(batch, n))
        xb, yb = shard.x[idx], shard.y[idx]
        grad = xb.T @ (_sigmoid(xb @ w) - yb) / len(idx) + l2 * w
        w -= lr * grad
    return w


# --------------------------------------------------------------------------
# Compression: top-k sparsification + int8 quantization
# --------------------------------------------------------------------------
@dataclass
class Update:
    """What actually crosses the network for one worker in one round."""

    idx: np.ndarray  # indices of kept entries
    q: np.ndarray  # int8 quantized values
    scale: float  # float32 dequantization scale
    n_samples: int  # for weighted averaging
    dim: int

    @property
    def nbytes(self) -> int:
        idx_bytes = 2 if self.dim <= 0xFFFF else 4
        return len(self.idx) * (idx_bytes + 1) + SCALE_BYTES


def compress(delta: np.ndarray, k: int, n_samples: int) -> Update:
    k = max(1, min(k, delta.size))
    idx = np.argpartition(np.abs(delta), -k)[-k:]
    idx.sort()
    vals = delta[idx]
    peak = float(np.max(np.abs(vals)))
    scale = peak / 127.0 if peak > 0 else 1.0
    q = np.clip(np.round(vals / scale), -127, 127).astype(np.int8)
    return Update(idx=idx, q=q, scale=float(np.float32(scale)), n_samples=n_samples, dim=delta.size)


def decompress(u: Update) -> np.ndarray:
    out = np.zeros(u.dim)
    out[u.idx] = u.q.astype(np.float64) * u.scale
    return out


# --------------------------------------------------------------------------
# Worker and aggregator
# --------------------------------------------------------------------------
class Worker:
    def __init__(self, wid: int, shard: Shard, seed: int):
        self.wid = wid
        self.shard = shard
        self.rng = np.random.default_rng(seed)
        self.residual = np.zeros(shard.x.shape[1])  # error feedback memory

    def round(self, w_global: np.ndarray, steps: int, lr: float, batch: int, l2: float, topk: float) -> Update:
        w_local = local_sgd(w_global, self.shard, steps, lr, batch, l2, self.rng)
        delta = (w_local - w_global) + self.residual
        k = int(np.ceil(topk * delta.size))
        upd = compress(delta, k, n_samples=self.shard.x.shape[0])
        # What was not sent this round is carried into the next one.
        self.residual = delta - decompress(upd)
        return upd

    def raw_bytes(self) -> int:
        n, dp1 = self.shard.x.shape
        return n * ((dp1 - 1) * FLOAT_BYTES + 1)  # float32 features + 1 byte label


class Aggregator:
    """Sample-weighted FedAvg over decompressed deltas."""

    def __init__(self, dim: int):
        self.w = np.zeros(dim)
        self.version = 0

    def merge(self, updates: List[Update]) -> np.ndarray:
        total = sum(u.n_samples for u in updates)
        avg = sum(decompress(u) * (u.n_samples / total) for u in updates)
        self.w = self.w + avg
        self.version += 1
        return self.w


# --------------------------------------------------------------------------
# Experiment
# --------------------------------------------------------------------------
@dataclass
class Result:
    config: dict
    rounds: List[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def run(
    workers: int = 8,
    rounds: int = 30,
    local_steps: int = 10,
    lr: float = 0.3,
    batch: int = 64,
    l2: float = 1e-4,
    topk: float = 0.25,
    dim: int = 64,
    samples: int = 500,
    shift: float = 0.5,
    seed: int = 0,
    verbose: bool = False,
) -> Result:
    cfg = dict(locals())
    cfg.pop("verbose")
    rng = np.random.default_rng(seed)
    w_true = rng.normal(0.0, 1.0, size=dim + 1) / np.sqrt(dim)
    w_true *= 3.0

    shards = [make_domain_data(samples, w_true, rng, shift, (0.7, 1.4)) for _ in range(workers)]
    test = make_domain_data(4000, w_true, rng, shift, (0.7, 1.4))
    # Test set pools several fresh domains so it measures generalization, not one worker's view.
    test_parts = [make_domain_data(1000, w_true, rng, shift, (0.7, 1.4)) for _ in range(4)]
    test = Shard(np.vstack([t.x for t in test_parts]), np.concatenate([t.y for t in test_parts]))

    pool = Shard(np.vstack([s.x for s in shards]), np.concatenate([s.y for s in shards]))
    w_central = np.zeros(dim + 1)
    crng = np.random.default_rng(seed + 1)
    for _ in range(rounds * local_steps):
        w_central = local_sgd(w_central, pool, 1, lr, batch * workers, l2, crng)
    c_loss, c_acc = loss_and_acc(w_central, test)

    ws = [Worker(i, s, seed + 100 + i) for i, s in enumerate(shards)]
    agg = Aggregator(dim + 1)
    res = Result(config=cfg)
    sent = 0
    dense_sent = 0
    for r in range(1, rounds + 1):
        ups = [wk.round(agg.w, local_steps, lr, batch, l2, topk) for wk in ws]
        agg.merge(ups)
        sent += sum(u.nbytes for u in ups)
        dense_sent += workers * (dim + 1) * FLOAT_BYTES
        loss, acc = loss_and_acc(agg.w, test)
        res.rounds.append(dict(round=r, loss=loss, acc=acc, bytes_total=sent))
        if verbose and (r == 1 or r % 5 == 0 or r == rounds):
            print(f"round {r:3d}  loss {loss:.4f}  acc {acc:.3f}  sent {sent / 1024:7.1f} KiB")

    raw = sum(wk.raw_bytes() for wk in ws)
    res.summary = dict(
        federated_loss=res.rounds[-1]["loss"],
        federated_acc=res.rounds[-1]["acc"],
        centralized_loss=c_loss,
        centralized_acc=c_acc,
        acc_gap=c_acc - res.rounds[-1]["acc"],
        bytes_delta_w_total=sent,
        bytes_dense_delta_w_total=dense_sent,
        bytes_raw_data_total=raw,
        traffic_reduction_vs_raw=raw / sent,
        traffic_reduction_vs_dense=dense_sent / sent,
    )
    return res


def _print_summary(res: Result) -> None:
    s = res.summary
    print("\n=== Summary ===")
    print(f"federated    acc {s['federated_acc']:.3f}  loss {s['federated_loss']:.4f}")
    print(f"centralized  acc {s['centralized_acc']:.3f}  loss {s['centralized_loss']:.4f}  (gap {s['acc_gap']:+.3f})")
    print(f"delta-w sent (top-k + int8): {s['bytes_delta_w_total'] / 1024:9.1f} KiB")
    print(f"delta-w dense float32:       {s['bytes_dense_delta_w_total'] / 1024:9.1f} KiB")
    print(f"raw data (centralized):      {s['bytes_raw_data_total'] / 1024:9.1f} KiB")
    print(f"traffic reduction vs raw data: {s['traffic_reduction_vs_raw']:.1f}x")
    print(f"traffic reduction vs dense dw: {s['traffic_reduction_vs_dense']:.1f}x")
    print("Note: the saving against raw data depends on model size versus dataset size.")


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--rounds", type=int, default=30)
    p.add_argument("--local-steps", type=int, default=10)
    p.add_argument("--lr", type=float, default=0.3)
    p.add_argument("--topk", type=float, default=0.25, help="fraction of delta-w entries sent per round (0-1]")
    p.add_argument("--dim", type=int, default=64)
    p.add_argument("--samples", type=int, default=500, help="samples per worker")
    p.add_argument("--shift", type=float, default=0.5, help="domain randomization strength")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=str, default=None, help="write full results as JSON")
    a = p.parse_args(argv)
    res = run(
        workers=a.workers, rounds=a.rounds, local_steps=a.local_steps, lr=a.lr, topk=a.topk,
        dim=a.dim, samples=a.samples, shift=a.shift, seed=a.seed, verbose=True,
    )
    _print_summary(res)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            json.dump(dict(config=res.config, rounds=res.rounds, summary=res.summary), f, indent=2)
        print(f"\nresults written to {a.output}")


if __name__ == "__main__":
    main()
