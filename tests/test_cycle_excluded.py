import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cycle_excluded import cycle_template


class CycleExclusionChecks(unittest.TestCase):
    def test_fixed_period_template_does_not_learn_from_its_own_cycle_group(self):
        t = np.arange(0, 27, 0.003)
        period = 0.373
        y = 1 + 0.01 * np.sin(2 * np.pi * t / period)
        cycle = np.floor(t / period).astype(int)
        original = cycle_template(t, y, period)
        injected = y.copy()
        injected[cycle == 20] -= 0.002
        changed = cycle_template(t, injected, period)
        np.testing.assert_array_equal(original[cycle % 3 == 2], changed[cycle % 3 == 2])
        self.assertLess(np.std(y - original), 0.04 * np.std(y))


if __name__ == "__main__":
    unittest.main()
