"""Scientific equivalence checks against unmodified Astropy, not self-mocks."""

from pathlib import Path
import sys
import unittest
import numpy as np
from astropy.timeseries import BoxLeastSquares

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from parallel_bls import ParallelBoxLeastSquares


class ParallelBLSChecks(unittest.TestCase):
    def test_identical_heteroskedastic_gapped_grid(self):
        rng = np.random.default_rng(98117)
        t = np.r_[np.arange(0, 12, 0.04), np.arange(730, 742, 0.04)]
        e = rng.uniform(0.001, 0.003, len(t))
        y = 1 + rng.normal(0, e)
        y[np.abs((t - 1.4 + 2.13) % 4.26 - 2.13) < 0.07] -= 0.015
        p = np.geomspace(2, 14, 1003)
        # Non-sorted inputs test restoration of the exact supplied order.
        p = p[rng.permutation(len(p))]
        for objective in ["likelihood", "snr"]:
            expected = BoxLeastSquares(t, y, e).power(p, [0.06, 0.14, 0.25], objective=objective)
            actual = ParallelBoxLeastSquares(t, y, e, threads=2, min_periods=1).power(
                p, [0.06, 0.14, 0.25], objective=objective
            )
            self.assertEqual(set(expected), set(actual))
            for key in expected:
                np.testing.assert_equal(actual[key], expected[key], err_msg=key)

    def test_scalar_fallback_and_invalid_duration(self):
        t = np.arange(0, 10, 0.1)
        y = 1 + 0.001 * np.sin(t)
        original = BoxLeastSquares(t, y)
        parallel = ParallelBoxLeastSquares(t, y, min_periods=1)
        for key, value in original.power(3, 0.1).items():
            np.testing.assert_equal(parallel.power(3, 0.1)[key], value)
        with self.assertRaises(ValueError):
            parallel.power(np.array([1.0, 2.0, 3.0]), 1.5)


if __name__ == "__main__":
    unittest.main()
