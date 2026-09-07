from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from repeated_search import make_repeated_search


class RepeatedSearchChecks(unittest.TestCase):
    def test_training_selection_cannot_use_held_sector_flux(self):
        rng = np.random.default_rng(9820)
        times = [np.arange(i * 30, i * 30 + 22, 10 / 1440) for i in range(6)]
        t = np.concatenate(times)
        sectors = np.concatenate([np.full(len(a), i + 1) for i, a in enumerate(times)])
        y = 1 + rng.normal(0, 0.0004, len(t))
        period, epoch, duration = 10.2, 1.3, 0.05
        y[abs((t - epoch + period / 2) % period - period / 2) < duration / 2] -= 0.0018
        data = pd.DataFrame(dict(time=t, flux=y, err=0.0004, sector=sectors))
        star = SimpleNamespace(Rad=0.2, Mass=0.2, Teff=3100)
        changed = data.copy()
        held = changed.sector.isin([2, 5])
        changed.loc[held, "flux"] = 2 - changed.loc[held, "flux"]
        with tempfile.TemporaryDirectory() as tmp, patch("repeated_search.MAX_REFINED", 12):
            run = make_repeated_search()
            a = run(data, star, Path(tmp) / "positive", max_signals=1)
            b = run(changed, star, Path(tmp) / "negative", max_signals=1)
        x, z = a["signals"][0], b["signals"][0]
        self.assertAlmostEqual(x["period_days"], period, delta=0.001)
        for key in ["period_days", "epoch_btjd", "duration_days", "depth", "event_ranking"]:
            self.assertEqual(x[key], z[key])
        self.assertGreater(x["holdout"]["fixed_ephemeris_snr"], 5)
        self.assertLess(z["holdout"]["fixed_ephemeris_snr"], -5)


if __name__ == "__main__":
    unittest.main()
