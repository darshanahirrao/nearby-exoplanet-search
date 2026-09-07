"""Experimental sector-local phase templates excluding each cycle group."""

import inspect

import numpy as np
from astropy.timeseries import LombScargle
from scipy.optimize import minimize_scalar

import variability
from physics import stellar_hz
from search import robust_sigma

PRODUCTION_CLEAN = variability.clean_variability


def weak_harmonic(df, star):
    # Execute the exact production function with only its threshold changed.
    # Both this adapter and the original source are hashed in the experiment plan.
    source = inspect.getsource(PRODUCTION_CLEAN)
    old = "if power[k] < 0.10:"
    if source.count(old) != 1:
        raise ValueError("The production threshold changed; re-review this comparison")
    namespace = dict(vars(variability))
    exec(
        compile(source.replace(old, "if power[k] < 0.02:"), "<weak-harmonic-comparison>", "exec"),
        namespace,
    )
    return namespace["clean_variability"](df, star)


def cycle_template(t, y, period, bins=64):
    phase = ((t - t.min()) / period) % 1
    cycles = np.floor((t - t.min()) / period).astype(int)
    index = np.minimum((phase * bins).astype(int), bins - 1)
    centers = (np.arange(bins) + 0.5) / bins
    prediction = np.empty(len(t))
    for group in range(3):
        test = cycles % 3 == group
        train = ~test
        medians = np.array(
            [
                np.median(y[train & (index == k)]) if np.sum(train & (index == k)) >= 5 else np.nan
                for k in range(bins)
            ]
        )
        valid = np.isfinite(medians)
        if valid.sum() < 0.75 * bins:
            raise ValueError("Too few populated phase bins")
        xp, fp = centers[valid], medians[valid]
        prediction[test] = np.interp(phase[test], np.r_[xp - 1, xp, xp + 1], np.tile(fp, 3))
    return prediction


def clean_cycles(df, star):
    result = df.copy()
    records = []
    minimum = max(0.5, 2 / stellar_hz(star)["inner_period"])
    for sector, data in df.groupby("sector"):
        if len(data) < 300 or np.ptp(data.time) < 2:
            continue
        t, y, error = (data[k].to_numpy() for k in ["time", "flux", "err"])
        t = t - np.median(t)
        ls = LombScargle(t, y, error)
        f, power = ls.autopower(minimum_frequency=minimum, maximum_frequency=25, samples_per_peak=5)
        k = int(np.argmax(power))
        record = dict(sector=int(sector), peak_fractional_power=float(power[k]), applied=False)
        if power[k] < 0.02:
            records.append(record)
            continue
        step = f[1] - f[0]
        fitted = minimize_scalar(
            lambda frequency: -ls.power(frequency),
            bounds=(max(minimum, f[k] - step), min(25, f[k] + step)),
            method="bounded",
        )
        period = 1 / fitted.x
        bins = min(128, max(16, len(t) // 50))
        record.update(period_days=float(period), bins=bins)
        if np.ptp(t) / period < 12:
            record["skip_reason"] = "Fewer than twelve variability cycles"
            records.append(record)
            continue
        try:
            model = cycle_template(t, y, period, bins)
        except ValueError as exc:
            record["skip_reason"] = str(exc)
            records.append(record)
            continue
        corrected = y - model + np.median(model)
        corrected /= np.median(corrected)
        before, after = robust_sigma(y), robust_sigma(corrected)
        record.update(original_scatter=float(before), corrected_scatter=float(after))
        if after <= 0.995 * before:
            result.loc[data.index, "flux"] = corrected
            result.loc[data.index, "err"] = np.maximum(
                error, robust_sigma(np.diff(corrected)) / np.sqrt(2)
            )
            record["applied"] = True
        records.append(record)
    return result, records
