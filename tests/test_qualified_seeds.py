from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qualified_seeds import make_search, training_flags


class QualifiedSeedChecks(unittest.TestCase):
    def test_holdout_flux_cannot_change_qualified_ephemeris(self):
        rng = np.random.default_rng(762)
        sectors = [1, 2, 3, 4, 5, 6]
        times = [np.arange(i * 32, i * 32 + 22, 10 / 1440) for i in range(6)]
        t = np.concatenate(times)
        sector = np.concatenate([np.full(len(ti), s) for s, ti in zip(sectors, times)])
        period, epoch, duration = 10.1, 1.7, 0.045
        y = 1 + rng.normal(0, 0.0006, len(t))
        y[abs((t - epoch + period / 2) % period - period / 2) < duration / 2] -= 0.0018
        df = pd.DataFrame(dict(time=t, flux=y, err=0.0006, sector=sector))
        star = SimpleNamespace(Rad=0.2, Mass=0.2, Teff=3100)
        run = make_search()
        with tempfile.TemporaryDirectory() as tmp:
            first = run(df, star, Path(tmp) / "original", max_signals=1)
            changed = df.copy()
            changed.loc[changed.sector.isin([2, 5]), "flux"] = (
                2 - changed.loc[changed.sector.isin([2, 5]), "flux"]
            )
            second = run(changed, star, Path(tmp) / "changed", max_signals=1)
        a, b = first["signals"][0], second["signals"][0]
        self.assertAlmostEqual(a["period_days"], period, delta=0.001)
        self.assertEqual(
            (a["period_days"], a["epoch_btjd"], a["duration_days"]),
            (b["period_days"], b["epoch_btjd"], b["duration_days"]),
        )
        self.assertGreater(a["holdout"]["fixed_ephemeris_snr"], 5)
        self.assertLess(b["holdout"]["fixed_ephemeris_snr"], -5)
        self.assertFalse(training_flags(a))
        a["discovery"]["single_event_power_fraction"] = 0.9
        self.assertIn("dominated_by_one_event", training_flags(a))


if __name__ == "__main__":
    unittest.main()
