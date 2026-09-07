from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from physics import stellar_hz
from portfolio_search import make_portfolio_search


class PortfolioChecks(unittest.TestCase):
    def test_multiple_training_signals_can_survive_the_old_two_fit_limit(self):
        rng = np.random.default_rng(91743)
        times = [np.arange(i * 37, i * 37 + 28, 10 / 1440) for i in range(6)]
        t = np.concatenate(times)
        sectors = np.concatenate([np.full(len(x), i + 1) for i, x in enumerate(times)])
        star = SimpleNamespace(Rad=0.2, Mass=0.2, Teff=3100)
        hz = stellar_hz(star)
        periods = np.linspace(hz["inner_period"] * 1.1, hz["outer_period"] * 0.85, 3)
        y = 1 + rng.normal(0, 0.0003, len(t))
        for period, epoch in zip(periods, [1.3, 2.1, 3.7]):
            y[abs((t - epoch + period / 2) % period - period / 2) < 0.025] -= 0.002
        data = pd.DataFrame(dict(time=t, flux=y, err=0.0003, sector=sectors))
        with tempfile.TemporaryDirectory() as tmp, patch("repeated_search.MAX_REFINED", 24):
            result = make_portfolio_search()(data, star, Path(tmp) / "original", max_signals=4)
            changed = data.copy()
            held = changed.sector.isin([2, 5])
            changed.loc[held, "flux"] = 2 - changed.loc[held, "flux"]
            reversed_holdout = make_portfolio_search()(
                changed, star, Path(tmp) / "reversed", max_signals=4
            )
        self.assertLessEqual(len(result["signals"]), 4)
        self.assertEqual(result["search_config"]["maximum_trial_fits"], 4)
        fields = ["period_days", "epoch_btjd", "duration_days", "depth", "event_ranking"]
        self.assertEqual(
            [[s[k] for k in fields] for s in result["signals"]],
            [[s[k] for k in fields] for s in reversed_holdout["signals"]],
        )
        for period in periods:
            self.assertTrue(
                any(abs(s["period_days"] / period - 1) < 0.001 for s in result["signals"]),
                str(period),
            )


if __name__ == "__main__":
    unittest.main()
