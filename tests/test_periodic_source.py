import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from periodic_source_experiment import compensated_residuals, fit_weights


class PeriodicSourceChecks(unittest.TestCase):
    def test_compensation_removes_a_linear_trend_with_partial_bins(self):
        rng = np.random.default_rng(601)
        t = np.arange(0, 12, 10 / 1440)
        t = t[rng.random(len(t)) > 0.15]
        residual = compensated_residuals(t, 3 + 0.02 * t)
        self.assertGreater(len(residual), 50)
        np.testing.assert_allclose(residual, 0, atol=3e-14)

    def test_separate_periodic_source_is_suppressed_without_losing_a_target_transit(self):
        rng = np.random.default_rng(602)
        t = np.arange(1200) * 10 / 1440
        target = np.array([0.7, 0.3, 0.0])
        neighbor = np.array([0.0, 0.3, 0.7])
        b = np.array([1.0, 1.0, 0.0])
        wave = 12 * np.sin(2 * np.pi * t / 0.3777)
        training = rng.normal(size=(len(t), 3)) + wave[:, None] * neighbor
        w, d = fit_weights(t, training, target[None, :], np.ones(3), b, period=0.3777)
        self.assertIsNone(d["fallback_reason"])
        self.assertGreaterEqual(w @ target, 1 - 1e-7)
        self.assertLessEqual(w @ w, b @ b + 1e-7)
        self.assertLess(abs(w @ neighbor), 0.2 * abs(b @ neighbor))
        held = rng.normal(size=(len(t), 3)) + wave[:, None] * neighbor
        transit = np.zeros(len(t))
        transit[502:509] = -0.3
        changed = held + transit[:, None] * target
        np.testing.assert_allclose(changed @ w - held @ w, transit * (w @ target), atol=1e-12)

    def test_a_coincident_source_cannot_be_nulled_without_losing_target_response(self):
        rng = np.random.default_rng(603)
        t = np.arange(1200) * 10 / 1440
        target = np.array([0.7, 0.3, 0.0])
        b = np.array([1.0, 1.0, 0.0])
        x = rng.normal(size=(len(t), 3)) + 15 * np.sin(2 * np.pi * t / 0.3777)[:, None] * target
        w, _ = fit_weights(t, x, target[None, :], np.ones(3), b, period=0.3777)
        self.assertGreaterEqual(w @ target, 1 - 1e-7)


if __name__ == "__main__":
    unittest.main()
