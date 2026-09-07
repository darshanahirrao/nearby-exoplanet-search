from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from realistic_injections import model_flux, total_duration
except ModuleNotFoundError as exc:
    if exc.name not in ["batman", "setuptools"]:
        raise
    model_flux = None


@unittest.skipIf(model_flux is None, "Optional batman-package dependency is not installed")
class RealisticInjectionChecks(unittest.TestCase):
    def test_uniform_central_depth_and_contacts_agree_with_geometry(self):
        star = SimpleNamespace(Rad=0.2, Mass=0.2)
        case = dict(
            period_days=9.2,
            epoch_btjd=3.0,
            radius_earth=1.0,
            impact_parameter=0.0,
            limb_darkening=[0.0, 0.0],
        )
        duration = total_duration(case, star)
        t = np.array(
            [case["epoch_btjd"] - duration, case["epoch_btjd"], case["epoch_btjd"] + duration]
        )
        flux = model_flux(t, case, star, exposure_days=1e-7)
        self.assertAlmostEqual(1 - flux[1], (0.0091577 / star.Rad) ** 2, places=10)
        np.testing.assert_allclose(flux[[0, 2]], 1, atol=1e-12)

    def test_limb_darkening_exposure_integration_and_null(self):
        star = SimpleNamespace(Rad=0.16, Mass=0.15)
        case = dict(
            period_days=7.8,
            epoch_btjd=10.0,
            radius_earth=0.8,
            impact_parameter=0.7,
            limb_darkening=[0.3, 0.2],
        )
        t = np.linspace(9.93, 10.07, 401)
        flux = model_flux(t, case, star)
        self.assertTrue(np.all(np.isfinite(flux)))
        self.assertGreater(float(flux.min()), 0)
        self.assertLess(float(flux.min()), 0.999)
        np.testing.assert_allclose(flux, flux[::-1], atol=1e-10)
        case["radius_earth"] = 0
        np.testing.assert_array_equal(model_flux(t, case, star), 1)


if __name__ == "__main__":
    unittest.main()
