"""Check coordinate transport and the separation of fit and held-view scoring."""

from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cross_view_experiment import Frame, evaluate, kernel


class CrossViewChecks(unittest.TestCase):
    def test_rotated_views_and_held_image_do_not_change_fitted_position(self):
        frames = []
        for angle in [0, 0.35, 2.6]:
            matrix = 21 * np.array(
                [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
            )
            frames.append(
                Frame(
                    dict(
                        error=np.ones((11, 11)),
                        target=np.array([5.0, 5.0]),
                        sky_matrix=matrix,
                        aperture=np.ones((11, 11), bool),
                    )
                )
            )
        offset = np.array([21.0, -10.5])
        images = [100 * kernel(frame.shape, frame.xy(offset)) for frame in frames]
        first = evaluate(frames, images)
        second = evaluate(frames, images[:-1] + [-images[-1]])
        np.testing.assert_equal(first["fitted_sky_offset_arcsec"], offset)
        np.testing.assert_equal(
            first["fitted_sky_offset_arcsec"], second["fitted_sky_offset_arcsec"]
        )
        self.assertGreater(first["held_prediction_nominal_snr"], 10)
        self.assertLess(second["held_prediction_nominal_snr"], -10)
        self.assertFalse(first["cross_view_accept"])


if __name__ == "__main__":
    unittest.main()
