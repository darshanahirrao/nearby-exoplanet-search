"""Experimental BLS duration prior, applied before selecting trial peaks."""

import numpy as np

from parallel_bls import ParallelBoxLeastSquares
from physics import central_duration


class PhysicalDurationBLS(ParallelBoxLeastSquares):
    def __init__(self, *args, star, **kwargs):
        super().__init__(*args, **kwargs)
        self.star = star

    def power(self, period, duration, objective=None, method=None, oversample=10):
        # This experiment only accepts the plain, sorted, positive arrays used
        # by longbaseline.py. The frozen production class remains unchanged.
        periods = np.asarray(period, dtype=float)
        if (
            periods.ndim != 1
            or not len(periods)
            or np.any(np.diff(periods) < 0)
            or np.any(periods <= 0)
        ):
            raise ValueError("Expected a nonempty sorted positive period array")
        bands = np.floor(np.log(periods / periods[0]) / np.log(1.25)).astype(int)
        parts = []
        for band in np.unique(bands):
            selected = periods[bands == band]
            central = central_duration(selected[0], self.star, radius_earth=2)
            durations = np.unique(
                np.clip(central * np.array([0.35, 0.5, 0.7, 1, 1.25, 1.5]), 0.015, 0.3)
            )
            parts.append(
                super().power(
                    selected, durations, objective=objective, method=method, oversample=oversample
                )
            )
        result = parts[0]
        for key, value in list(result.items()):
            if isinstance(value, np.ndarray):
                result[key] = np.concatenate([part[key] for part in parts])
            elif any(part[key] != value for part in parts[1:]):
                raise ValueError(f"Inconsistent BLS metadata: {key}")
        return result
