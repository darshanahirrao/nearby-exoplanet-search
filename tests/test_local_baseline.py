import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from local_baseline import continuum_event


class LocalBaselineTests(unittest.TestCase):
    def frame(self):
        rng = np.random.default_rng(84023)
        t = np.sort(rng.uniform(-0.39, 0.39, 210))
        e = rng.uniform(0.0004, 0.0011, len(t))
        flux = 1 + 0.0005 + 0.002 * t + 0.020 * t**2 - 0.0012 * (abs(t) < 0.05)
        return pd.DataFrame(dict(time=t, flux=flux, err=e))

    def test_known_transit_on_curved_continuum(self):
        data = self.frame()
        result = continuum_event(data, 0, 0.1, degree=2)
        self.assertAlmostEqual(result["depth"], 0.0012, places=12)
        biased = continuum_event(data, 0, 0.1, degree=0)
        self.assertGreater(abs(biased["depth"] - 0.0012), 0.0005)

    def test_covariance_matches_independent_noise_realizations(self):
        rng = np.random.default_rng(7844)
        data = self.frame()
        nominal = continuum_event(data, 0, 0.1, degree=2)
        measured = []
        for _ in range(500):
            noisy = data.copy()
            noisy["flux"] += rng.normal(size=len(data)) * data.err.to_numpy()
            measured.append(continuum_event(noisy, 0, 0.1, degree=2)["depth"])
        self.assertLess(abs(np.std(measured, ddof=1) / nominal["error"] - 1), 0.12)

    def test_missing_flank_is_not_extrapolated(self):
        data = self.frame()
        result = continuum_event(data[data.time > -0.1], 0, 0.1, degree=2)
        self.assertEqual(result["status"], "insufficient_two_sided_coverage")
        self.assertNotIn("depth", result)


if __name__ == "__main__":
    unittest.main()
