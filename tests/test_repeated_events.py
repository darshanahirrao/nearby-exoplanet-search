from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from repeated_events import EventContrasts
from search import event_checks


class RepeatedEventChecks(unittest.TestCase):
    def test_prefix_contrasts_match_original_on_gaps_and_unequal_errors(self):
        rng = np.random.default_rng(2091)
        t = np.arange(0, 90, 10 / 1440)
        t = t[((t % 27) < 21) & (rng.random(len(t)) > 0.15)]
        error = rng.uniform(0.0005, 0.0015, len(t))
        flux = 1 + rng.normal(0, error)
        flux[abs((t - 1.28 + 4.1) % 8.2 - 4.1) < 0.04] -= 0.002
        frame = pd.DataFrame(dict(time=t, flux=flux, err=error))
        quick = EventContrasts(frame)
        for period, epoch, duration in [(8.2, 1.28, 0.08), (13.89, 0.93, 0.035), (4.7, 1.1, 0.13)]:
            expected = event_checks(frame, period, epoch, duration)
            measured = quick.measure(period, epoch, duration)
            self.assertEqual(measured["n_events"], expected["n_observed_events"])
            self.assertAlmostEqual(measured["total_snr"], expected["fixed_ephemeris_snr"], places=8)
            records = expected["event_snr"]
            omitted = []
            for i in range(len(records)):
                left = [r for j, r in enumerate(records) if i != j]
                omitted.append(
                    sum(r["depth"] / r["error"] ** 2 for r in left)
                    / np.sqrt(sum(1 / r["error"] ** 2 for r in left))
                )
            self.assertAlmostEqual(
                measured["leave_one_out_snr"],
                min(expected["fixed_ephemeris_snr"], min(omitted)),
                places=8,
            )

    def test_single_deep_dip_cannot_supply_repeated_event_score(self):
        t = np.arange(0, 40, 10 / 1440)
        y = np.ones(len(t))
        y[abs(t - 1.2) < 0.05] -= 0.02
        frame = pd.DataFrame(dict(time=t, flux=y, err=0.001))
        isolated = EventContrasts(frame).measure(7.7, 1.2, 0.1)
        self.assertGreater(isolated["total_snr"], 20)
        self.assertAlmostEqual(isolated["leave_one_out_snr"], 0, places=8)
        frame.loc[abs((t - 1.2 + 7.7 / 2) % 7.7 - 7.7 / 2) < 0.05, "flux"] = 0.998
        repeated = EventContrasts(frame).measure(7.7, 1.2, 0.1)
        self.assertGreater(repeated["leave_one_out_snr"], 10)


if __name__ == "__main__":
    unittest.main()
