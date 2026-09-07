from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from astropy.io import fits

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from realistic_injections import make_loader, model_flux, total_duration
    import search
except ModuleNotFoundError as exc:
    if exc.name not in ["batman", "setuptools"]:
        raise
    model_flux = None


@unittest.skipIf(model_flux is None, "Optional batman-package dependency is not installed")
class RealisticInjectionChecks(unittest.TestCase):
    def test_physical_shape_is_applied_before_binning_in_the_fits_loader(self):
        star = SimpleNamespace(Rad=0.2, Mass=0.2)
        case = dict(
            period_days=3.9,
            epoch_btjd=1.1,
            radius_earth=0.8,
            impact_parameter=0.55,
            limb_darkening=[0.4, 0.2],
        )
        case["duration_days"] = total_duration(case, star)
        t = np.arange(0, 12, 2 / 1440)
        injected = dict(
            period=case["period_days"],
            epoch=case["epoch_btjd"],
            depth=(case["radius_earth"] * 0.0091577 / star.Rad) ** 2,
            duration=case["duration_days"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "data/lightcurves/888"
            folder.mkdir(parents=True)
            primary = fits.PrimaryHDU()
            primary.header["SECTOR"] = 1
            table = fits.BinTableHDU.from_columns(
                [
                    fits.Column(name="TIME", format="D", array=t),
                    fits.Column(name="PDCSAP_FLUX", format="D", array=np.full(len(t), 10000.0)),
                    fits.Column(name="PDCSAP_FLUX_ERR", format="D", array=np.full(len(t), 3.0)),
                    fits.Column(name="QUALITY", format="J", array=np.zeros(len(t), dtype=int)),
                ]
            )
            fits.HDUList([primary, table]).writeto(folder / "fixture_lc.fits")
            with patch.object(search, "ROOT", Path(tmp)):
                loader = make_loader(case, star)
                actual, _ = loader(888, inject=injected)
                box, _ = search.load_target(888, inject=injected)
        expected = model_flux(t, case, star)
        bt, by, _ = search.bin_series(t, expected, np.full(len(t), 0.0003))
        # The isolated short dips cannot change the surrounding constant median
        # trend. The physical model must reach the loader before ten-minute bins.
        np.testing.assert_allclose(actual.flux, np.interp(actual.time, bt, by), atol=2e-12, rtol=0)
        np.testing.assert_allclose(actual.time, box.time, atol=1e-12, rtol=0)
        self.assertGreater(float(np.max(abs(actual.flux - box.flux))), 1e-5)

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
