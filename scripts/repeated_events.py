"""Fast local event contrasts and leave-one-event-out ranking diagnostics.

The nominal errors are those of the original pipeline. Overlapping local
baseline windows can correlate events; these scores are ranking diagnostics,
not calibrated significance or false-alarm probabilities.
"""

import numpy as np


class EventContrasts:
    def __init__(self, frame):
        ordered = frame.sort_values("time")
        self.time = ordered.time.to_numpy()
        weight = 1 / ordered.err.to_numpy() ** 2
        self.weight = np.r_[0.0, np.cumsum(weight)]
        self.flux = np.r_[0.0, np.cumsum(weight * (ordered.flux.to_numpy() - 1))]

    def window(self, left, right):
        a = np.searchsorted(self.time, left, side="right")
        b = np.searchsorted(self.time, right, side="left")
        return b - a, self.weight[b] - self.weight[a], self.flux[b] - self.flux[a]

    def measure(self, period, epoch, duration):
        cycles = np.arange(
            np.floor((self.time[0] - epoch) / period),
            np.ceil((self.time[-1] - epoch) / period) + 1,
        )
        centers = epoch + cycles * period
        inside, wi, yi = self.window(centers - duration / 2, centers + duration / 2)
        outer = max(4 * duration, 0.3)
        nl, wl, yl = self.window(centers - outer, centers - duration)
        nr, wr, yr = self.window(centers + duration, centers + outer)
        wo, yo = wl + wr, yl + yr
        good = (inside >= 3) & (nl + nr >= 8) & (wi > 0) & (wo > 0)
        if not good.any():
            return dict(n_events=0, total_snr=0.0, leave_one_out_snr=None)
        depth = yo[good] / wo[good] - yi[good] / wi[good]
        weights = 1 / (1 / wi[good] + 1 / wo[good])
        contribution = weights * depth
        denominator, numerator = weights.sum(), contribution.sum()
        total = numerator / np.sqrt(denominator)
        leave_one_out = (
            float(
                np.minimum(
                    total, np.min((numerator - contribution) / np.sqrt(denominator - weights))
                )
            )
            if good.sum() >= 3
            else None
        )
        return dict(
            n_events=int(good.sum()),
            total_snr=float(total),
            leave_one_out_snr=leave_one_out,
        )


def distinct_peaks(power, baseline, low, high, maximum=4096):
    """Same resolution exclusion as qualified_seeds; rank once instead of repeated argmax."""
    periods = np.asarray(power.period)
    available = np.isfinite(power.power) & (periods >= low) & (periods <= high)
    indices = []
    order = np.argsort(-np.where(available, power.power, -np.inf), kind="stable")
    for index in order:
        if not available[index]:
            continue
        indices.append(int(index))
        width = 2 * power.duration[index] / baseline
        left = np.searchsorted(periods, periods[index] * (1 - width), side="left")
        right = np.searchsorted(periods, periods[index] * (1 + width), side="right")
        available[left:right] = False
        if len(indices) == maximum:
            break
    return indices
