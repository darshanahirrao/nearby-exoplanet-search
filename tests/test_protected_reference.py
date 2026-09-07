import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from protected_reference_experiment import (
    apply,
    bases,
    diagonal_noise,
    projection_fraction,
    reference_weights,
)


class ProtectedReferenceChecks(unittest.TestCase):
    def test_reference_rejects_target_and_declines_identical_sources(self):
        p = np.array([0.7, 0.3, 0])
        n = np.array([0, 0.3, 0.7])
        noise = np.array([2.0, 1.0, 4.0])
        q, reason = reference_weights(p, n, noise)
        self.assertIsNone(reason)
        np.testing.assert_allclose([q @ p, q @ n], [0, 1], atol=1e-12)
        q, reason = reference_weights(p, p, noise)
        self.assertIsNotNone(reason)
        np.testing.assert_array_equal(q, 0)

    def test_dense_noise_operator_matches_fast_covariance_and_injection_response(self):
        rng = np.random.default_rng(713)
        t = np.sort(rng.uniform(0, 12, 110))
        trend, modes = bases(t)
        b = np.array([1.0, 1.0, 0])
        q = np.array([-0.4, 0.9, 1.2])
        coefficient = 0.35
        error = rng.uniform(0.8, 1.3, (len(t), 3))
        l = modes @ modes.T
        dense = np.eye(len(t))[:, :, None] * b - coefficient * l[:, :, None] * q
        exact = np.sum((dense * error[None, :, :]) ** 2, axis=(1, 2))
        np.testing.assert_allclose(
            diagonal_noise(error, b, q, modes, coefficient), exact, rtol=1e-12
        )
        u = (abs((t - 0.7 + 3.2) % 6.4 - 3.2) < 0.15).astype(float)
        p = np.array([0.6, 0.35, 0.05])
        f = projection_fraction(u, trend, modes)
        filtered = apply(u[:, None] * p, b, q, modes, coefficient)
        residual = u - trend @ (trend.T @ u)
        response = (residual @ filtered) / (residual @ u) / (b @ p)
        self.assertAlmostEqual(response, 1 - coefficient * (q @ p) / (b @ p) * f, places=12)


if __name__ == "__main__":
    unittest.main()
