"""Evaluate the unchanged Astropy BLS grid in ordered, disjoint thread chunks.

Astropy's fast C implementation releases the GIL. This adapter only schedules
independent periods; it retains every period, duration and sample. Unsupported
input types and small grids use the original implementation directly.
"""

from concurrent.futures import ThreadPoolExecutor
import numpy as np
from astropy.timeseries import BoxLeastSquares


class ParallelBoxLeastSquares(BoxLeastSquares):
    def __init__(self, *args, threads=2, min_periods=3000, **kwargs):
        super().__init__(*args, **kwargs)
        if threads < 1:
            raise ValueError("threads must be positive")
        self.threads = int(threads)
        self.min_periods = int(min_periods)

    def power(self, period, duration, objective=None, method=None, oversample=10):
        original = super().power
        options = dict(objective=objective, method=method, oversample=oversample)
        # Keep the public Astropy behavior for quantities and absolute times.
        if (
            self.threads == 1
            or method == "slow"
            or not isinstance(period, np.ndarray)
            or type(period) is not np.ndarray
            or period.ndim != 1
            or len(period) < self.min_periods
            or self._tstart is not None
            or getattr(self.y, "unit", None) is not None
            or getattr(self._trel, "unit", None) is not None
            or getattr(duration, "unit", None) is not None
        ):
            return original(period, duration, **options)
        # Several interleaved chunks balance long and short periods. Restoring
        # the original order also preserves argmax tie-breaking downstream.
        count = min(len(period), 4 * self.threads)
        indices = [np.arange(i, len(period), count) for i in range(count)]
        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            parts = list(pool.map(lambda ix: original(period[ix], duration, **options), indices))
        result = parts[0]
        order = np.argsort(np.concatenate(indices))
        for key, value in parts[0].items():
            if isinstance(value, np.ndarray):
                result[key] = np.concatenate([part[key] for part in parts])[order]
            elif any(part[key] != value for part in parts[1:]):
                raise ValueError(f"Inconsistent BLS metadata: {key}")
        return result
