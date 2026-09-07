from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from physical_duration import PhysicalDurationBLS
from physics import central_duration


class PhysicalDurationChecks(unittest.TestCase):
    def test_short_transit_recovery_period_order_and_duration_bounds(self):
        rng = np.random.default_rng(9772)
        t = np.arange(0, 95, 10 / 1440)
        star = pd.Series(dict(Rad=0.18, Mass=0.18))
        y = 1 + rng.normal(0, 0.001, len(t))
        y[abs((t - 1.2 + 3.55) % 7.1 - 3.55) < 0.024] -= 0.006
        model = PhysicalDurationBLS(t, y, np.full(len(t), 0.001), star=star)
        periods = np.sort(np.r_[np.linspace(5, 10, 1000), 7.1])
        result = model.power(periods, [0.25], objective="likelihood", oversample=10)
        self.assertAlmostEqual(float(result.period[np.argmax(result.power)]), 7.1)
        np.testing.assert_array_equal(result.period, periods)
        self.assertTrue(np.all(result.duration <= 1.6 * central_duration(periods, star, 2)))
        with self.assertRaises(ValueError):
            model.power(periods[::-1], [0.05])


if __name__ == "__main__":
    unittest.main()
