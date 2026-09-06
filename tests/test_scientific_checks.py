"""Offline sanity checks; real-data validation is separately reported."""

import sys, unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from physics import stellar_hz, central_duration
from search import event_checks, split_campaigns
from refine import three_way_split, refine_signals
from variability import clean_variability


class ScientificChecks(unittest.TestCase):
    def test_sector_local_variability_filter_preserves_transits(self):
        rng = np.random.default_rng(8319)
        time = np.r_[np.arange(0, 27, 0.007), np.arange(400, 427, 0.007)]
        phase = (time - 1.23 + 5) % 10 - 5
        flux = 1 + 0.008 * np.sin(2 * np.pi * time / 0.51055) - 0.002 * (abs(phase) < 0.0275)
        flux += rng.normal(0, 0.0003, len(time))
        frame = pd.DataFrame(
            dict(
                time=time,
                flux=flux,
                err=np.full(len(time), 0.0003),
                sector=np.where(time < 100, 1, 20),
            )
        )
        star = SimpleNamespace(Rad=0.2, Mass=0.2, Teff=3200)
        clean, records = clean_variability(frame, star)
        self.assertTrue(all(r["applied"] for r in records))
        outside = abs(phase) > 0.1
        self.assertLess(np.std(clean.flux[outside]), np.std(frame.flux[outside]) / 5)
        depth = np.median(clean.flux[outside]) - np.median(clean.flux[abs(phase) < 0.0275])
        self.assertAlmostEqual(depth, 0.002, delta=0.0004)
        changed = frame.copy()
        changed.loc[changed.sector == 20, "flux"] += 0.03 * np.sin(time[changed.sector == 20])
        other, _ = clean_variability(changed, star)
        np.testing.assert_array_equal(clean.flux[clean.sector == 1], other.flux[other.sector == 1])

    def test_earth_units_and_hz_order(self):
        h = stellar_hz(SimpleNamespace(Rad=1, Mass=1, Teff=5772))
        self.assertAlmostEqual(h["earth_period"], 365.256, places=4)
        self.assertLess(h["inner_period"], h["earth_period"])
        self.assertGreater(h["outer_period"], h["earth_period"])
        for temp in np.linspace(2600, 4500, 15):
            h = stellar_hz(SimpleNamespace(Rad=0.2, Mass=0.2, Teff=temp))
            self.assertGreater(h["inner_flux"], 1)
            self.assertTrue(0 < h["outer_flux"] < 1)

    def test_earth_sun_central_duration(self):
        hours = 24 * central_duration(365.256, SimpleNamespace(Rad=1, Mass=1))
        self.assertTrue(12.9 < hours < 13.2)

    def test_event_depth_and_empty_holdout(self):
        t = np.arange(0, 40, 0.005) + 0.00123
        phase = (t - 1 + 2.5) % 5 - 2.5
        d = pd.DataFrame(
            dict(
                time=t, flux=1 - 0.001 * (abs(phase) < 0.06), err=np.full(len(t), 0.0002), sector=1
            )
        )
        r = event_checks(d, 5, 1, 0.12)
        self.assertEqual(r["n_observed_events"], 8)
        self.assertTrue(all(abs(x["depth"] - 0.001) < 1e-10 for x in r["event_snr"]))
        self.assertEqual(event_checks(d.iloc[:0], 5, 1, 0.12)["n_observed_events"], 0)

    def test_campaign_holdout_is_disjoint(self):
        t = np.r_[np.arange(0, 20, 0.02), np.arange(400, 410, 0.02)]
        d, v, _ = split_campaigns(pd.DataFrame(dict(time=t, sector=np.where(t < 100, 1, 20))))
        self.assertEqual((len(d), len(v)), (1000, 500))
        self.assertFalse(set(d.time) & set(v.time))

    def test_timing_refinement_recovers_without_holdout_leakage(self):
        rng = np.random.default_rng(1701)
        t = np.r_[np.arange(0, 70, 0.007), np.arange(400, 420, 0.007), np.arange(800, 825, 0.007)]
        sector = np.select([t < 100, t < 500], [1, 20], 40)
        period = 10.1234
        epoch = 1.234
        duration = 0.055
        phase = (t - epoch + period / 2) % period - period / 2
        flux = 1 - 0.002 * (abs(phase) < duration / 2) + rng.normal(0, 0.0003, len(t))
        df = pd.DataFrame(dict(time=t, flux=flux, err=np.full(len(t), 0.0003), sector=sector))
        star = SimpleNamespace(Rad=0.2, Mass=0.2, Teff=3200)
        seed = [
            dict(iteration=1, period_days=period + 0.001, epoch_btjd=epoch, duration_days=duration)
        ]
        d, r, h, _ = three_way_split(df)
        self.assertFalse(
            set(d.time) & set(r.time) | set(d.time) & set(h.time) | set(r.time) & set(h.time)
        )
        first = refine_signals(df, star, seed)
        changed = df.copy()
        changed.loc[changed.sector == 40, "flux"] = 2 - changed.loc[changed.sector == 40, "flux"]
        second = refine_signals(changed, star, seed)
        a = first["signals"][0]
        b = second["signals"][0]
        self.assertAlmostEqual(a["period_days"], period, delta=0.0003)
        self.assertEqual(a["period_days"], b["period_days"])
        self.assertEqual(a["epoch_btjd"], b["epoch_btjd"])
        self.assertGreater(a["holdout"]["fixed_ephemeris_snr"], 5)
        self.assertLess(b["holdout"]["fixed_ephemeris_snr"], -5)


if __name__ == "__main__":
    unittest.main()
