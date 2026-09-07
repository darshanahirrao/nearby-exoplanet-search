"""Reserved-view flux cannot change learned uncertainty weights or prediction."""

from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cross_view_experiment import Frame, kernel
from cross_view_uncertainty import evaluate, predictor


class UncertaintyPredictionChecks(unittest.TestCase):
    def test_prediction_is_frozen_before_reserved_flux(self):
        frames = []
        for angle in [0, 0.4, 2.8]:
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
        images = [40 * kernel(frame.shape, frame.target) for frame in frames]
        predicted, frozen = predictor(frames[:-1], images[:-1], frames[-1])
        self.assertAlmostEqual(np.linalg.norm(predicted), 1)
        self.assertGreater(frozen["effective_grid_positions"], 1)
        positive = evaluate(frames, images)
        negative = evaluate(frames, images[:-1] + [-images[-1]])
        for key in [
            "frozen_weights_sha256",
            "frozen_predictor_sha256",
            "training_near_target_weight",
        ]:
            self.assertEqual(positive[key], negative[key])
        self.assertGreater(positive["uncertainty_held_nominal_snr"], 5)
        self.assertLess(negative["uncertainty_held_nominal_snr"], -5)


if __name__ == "__main__":
    unittest.main()
