"""Tests for Pipeline/core/federated_aggregator.py. Run with: python -m pytest Pipeline/tests -q"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
import federated_aggregator as fa  # noqa: E402


class CompressionTests(unittest.TestCase):
    def test_topk_keeps_largest_magnitudes(self):
        delta = np.array([0.1, -5.0, 0.2, 3.0, -0.05, 0.0])
        u = fa.compress(delta, k=2, n_samples=10)
        self.assertEqual(sorted(u.idx.tolist()), [1, 3])

    def test_roundtrip_error_is_bounded_by_quantization_step(self):
        rng = np.random.default_rng(0)
        delta = rng.normal(size=200)
        u = fa.compress(delta, k=200, n_samples=1)
        back = fa.decompress(u)
        self.assertLessEqual(np.max(np.abs(back - delta)), u.scale / 2 + 1e-9)

    def test_dropped_entries_are_zero(self):
        delta = np.arange(1, 11, dtype=float)
        u = fa.compress(delta, k=3, n_samples=1)
        back = fa.decompress(u)
        self.assertEqual(np.count_nonzero(back), 3)

    def test_byte_count_matches_wire_format(self):
        u = fa.compress(np.ones(65), k=16, n_samples=1)
        self.assertEqual(u.nbytes, 16 * (2 + 1) + 4)

    def test_all_zero_delta_does_not_divide_by_zero(self):
        u = fa.compress(np.zeros(8), k=2, n_samples=1)
        self.assertTrue(np.all(fa.decompress(u) == 0))


class ErrorFeedbackTests(unittest.TestCase):
    def test_nothing_is_lost_only_deferred(self):
        rng = np.random.default_rng(1)
        shard = fa.make_domain_data(200, rng.normal(size=9), rng, 0.5, (0.7, 1.4))
        wk = fa.Worker(0, shard, seed=3)
        w0 = np.zeros(9)
        known_delta = np.linspace(-1.0, 1.0, 9)
        wk.residual = np.full(9, 0.05)
        original = fa.local_sgd
        fa.local_sgd = lambda w, *a, **k: w + known_delta  # fixed local update
        try:
            upd = wk.round(w0, steps=1, lr=0.0, batch=1, l2=0.0, topk=0.25)
        finally:
            fa.local_sgd = original
        sent = fa.decompress(upd)
        # sent + new residual == local delta + old residual: held-back mass is carried, not dropped
        np.testing.assert_allclose(sent + wk.residual, known_delta + 0.05, atol=1e-12)
        self.assertGreater(np.linalg.norm(wk.residual), 0.0)


class AggregatorTests(unittest.TestCase):
    def test_weighted_average(self):
        d = 6
        a = fa.compress(np.full(d, 2.0), k=d, n_samples=100)
        b = fa.compress(np.full(d, -1.0), k=d, n_samples=300)
        agg = fa.Aggregator(d)
        w = agg.merge([a, b])
        expected = (2.0 * 100 + -1.0 * 300) / 400
        np.testing.assert_allclose(w, np.full(d, expected), atol=0.05)
        self.assertEqual(agg.version, 1)


class EndToEndTests(unittest.TestCase):
    def test_federated_matches_centralized_and_saves_traffic(self):
        res = fa.run(seed=0)
        s = res.summary
        self.assertLess(abs(s["acc_gap"]), 0.03)
        self.assertGreater(s["traffic_reduction_vs_raw"], 10)
        self.assertGreater(s["traffic_reduction_vs_dense"], 1.5)

    def test_loss_decreases_from_first_round(self):
        res = fa.run(seed=2)
        self.assertLess(res.rounds[-1]["loss"], res.rounds[0]["loss"])

    def test_is_deterministic_for_a_seed(self):
        a = fa.run(seed=5, rounds=8)
        b = fa.run(seed=5, rounds=8)
        self.assertEqual(a.summary["federated_loss"], b.summary["federated_loss"])

    def test_smaller_topk_sends_fewer_bytes(self):
        lo = fa.run(seed=0, rounds=10, topk=0.05).summary["bytes_delta_w_total"]
        hi = fa.run(seed=0, rounds=10, topk=0.5).summary["bytes_delta_w_total"]
        self.assertLess(lo, hi)


if __name__ == "__main__":
    unittest.main()
