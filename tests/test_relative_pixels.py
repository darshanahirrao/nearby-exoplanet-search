"""An independent synthetic field with target variability and a contaminant."""

import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from relative_pixel_experiment import fit_weights


class RelativePixelChecks(unittest.TestCase):
    def test_transit_preservation_and_noise_caps_on_independent_samples(self):
        rng = np.random.default_rng(613)
        profile = np.array([0.7, 0.3, 0.0])
        contaminant = np.array([0.0, 0.5, 0.5])
        baseline = np.array([1.0, 1.0, 0.0])
        training = rng.normal(size=(1000, 3)) + rng.normal(0, 8, (1000, 1)) * contaminant
        w, diagnostics = fit_weights(training, profile[None, :], np.ones(3), baseline)
        self.assertIsNone(diagnostics["fallback_reason"])
        self.assertGreaterEqual(w @ profile, 1 - 1e-7)
        self.assertLessEqual(w @ w, baseline @ baseline + 1e-7)
        held = rng.normal(size=(1000, 3)) + rng.normal(0, 8, (1000, 1)) * contaminant
        self.assertLess(np.std(held @ w), 0.65 * np.std(held @ baseline))
        transit = np.zeros(1000)
        transit[401:409] = -0.5
        injected = held + transit[:, None] * profile
        np.testing.assert_allclose((injected @ w) - (held @ w), transit * (profile @ w), atol=1e-12)


if __name__ == "__main__":
    unittest.main()
