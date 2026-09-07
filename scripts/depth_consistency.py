"""Conservative event-scatter inflation for experimental ranking, not significance."""

import numpy as np

from repeated_events import EventContrasts


class ConsistentContrasts(EventContrasts):
    def measure(self, period, epoch, duration):
        result = super().measure(period, epoch, duration)
        result.update(
            reduced_depth_chi2=None, consistent_total_snr=None, consistent_leave_one_out_snr=None
        )
        if result["n_events"] < 3:
            return result
        cycles = np.arange(
            np.floor((self.time[0] - epoch) / period), np.ceil((self.time[-1] - epoch) / period) + 1
        )
        centers = epoch + cycles * period
        ni, wi, yi = self.window(centers - duration / 2, centers + duration / 2)
        outer = max(4 * duration, 0.3)
        nl, wl, yl = self.window(centers - outer, centers - duration)
        nr, wr, yr = self.window(centers + duration, centers + outer)
        wo, yo = wl + wr, yl + yr
        good = (ni >= 3) & (nl + nr >= 8) & (wi > 0) & (wo > 0)
        depth = yo[good] / wo[good] - yi[good] / wi[good]
        weight = 1 / (1 / wi[good] + 1 / wo[good])
        mean = np.sum(weight * depth) / sum(weight)
        q = float(np.sum(weight * (depth - mean) ** 2) / (len(depth) - 1))
        inflation = np.sqrt(max(1, q))
        result.update(
            reduced_depth_chi2=q,
            consistent_total_snr=result["total_snr"] / inflation,
            consistent_leave_one_out_snr=result["leave_one_out_snr"] / inflation,
        )
        return result
