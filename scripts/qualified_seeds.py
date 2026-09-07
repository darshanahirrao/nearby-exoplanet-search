"""Experimental early training checks; holdout evaluation stays unchanged."""

import inspect

import numpy as np

import longbaseline
from parallel_bls import ParallelBoxLeastSquares
from physical_duration import PhysicalDurationBLS
from physics import central_duration, stellar_hz
from search import event_checks

ORIGINAL_SEARCH = longbaseline.search_combined


def training_flags(signal):
    d = signal["discovery"]
    flags = []
    if d["n_observed_events"] < 3:
        flags.append("fewer_than_three_training_events")
    if (d.get("single_event_power_fraction") or 0) > 0.6:
        flags.append("dominated_by_one_event")
    if (d.get("odd_even_sigma") or 0) > 3:
        flags.append("odd_even_discrepancy")
    if not 0.5 <= signal["radius_earth_estimate"] <= 2:
        flags.append("outside_initial_small_planet_radius_range")
    if not signal["in_optimistic_hz"]:
        flags.append("outside_nominal_optimistic_hz")
    if signal["duration_days"] > 1.6 * signal["central_circular_duration_days"]:
        flags.append("long_relative_to_circular_transit")
    if signal["nominal_training_snr"] < 7:
        flags.append("low_nominal_training_snr")
    return flags


def select_training(
    training, coarse, star, periods, low, high, baseline, max_signals, qualified=True
):
    hz = stellar_hz(star)
    coarse_keep = np.ones(len(coarse), dtype=bool)
    full_keep = np.ones(len(training), dtype=bool)
    signals, diagnostics = [], []
    for iteration in range(1, max_signals + 1):
        model = PhysicalDurationBLS(
            coarse.time.to_numpy()[coarse_keep],
            coarse.flux.to_numpy()[coarse_keep],
            coarse.err.to_numpy()[coarse_keep],
            star=star,
        )
        power = model.power(periods, [0.04], objective="likelihood", oversample=5)
        full = ParallelBoxLeastSquares(
            training.time.to_numpy()[full_keep],
            training.flux.to_numpy()[full_keep],
            training.err.to_numpy()[full_keep],
        )
        available = np.isfinite(power.power)
        if qualified:
            available &= (periods >= hz["inner_period"]) & (periods <= hz["outer_period"])
        accepted = None
        for rank in range(1, (64 if qualified else 1) + 1):
            if not available.any():
                break
            k = int(np.argmax(np.where(available, power.power, -np.inf)))
            p0, duration0 = float(power.period[k]), float(power.duration[k])
            available &= abs(periods / p0 - 1) > 2 * duration0 / baseline
            step = periods[min(k + 1, len(periods) - 1)] - periods[max(0, k - 1)]
            fine = np.linspace(max(low, p0 - 2 * step), min(high, p0 + 2 * step), 301)
            expected = central_duration(p0, star)
            # Exact original refinement family; only seed search uses the prior.
            fine_durations = np.unique(
                np.clip(
                    np.r_[
                        duration0 * np.array([0.5, 0.75, 1]),
                        expected * np.array([0.5, 0.7, 1, 1.3]),
                    ],
                    0.015,
                    0.3,
                )
            )
            fitted = full.power(fine, fine_durations, objective="likelihood", oversample=15)
            best = int(np.argmax(fitted.power))
            period, epoch, duration, depth = (
                float(fitted[name][best])
                for name in ["period", "transit_time", "duration", "depth"]
            )
            radius = float(np.sqrt(max(0, depth)) * float(star.Rad) / 0.0091577)
            a = (float(star.Mass) * (period / 365.256) ** 2) ** (1 / 3)
            signal = dict(
                seed_iteration=iteration,
                training_peak_rank=rank,
                period_days=period,
                epoch_btjd=epoch,
                duration_days=duration,
                depth=depth,
                radius_earth_estimate=radius,
                irradiation_earth_estimate=hz["luminosity"] / a**2,
                nominal_training_snr=float(fitted.depth_snr[best]),
                coarse_snr=float(power.depth_snr[k]),
                discovery=event_checks(
                    training.iloc[np.flatnonzero(full_keep)], period, epoch, duration
                ),
                central_circular_duration_days=float(central_duration(period, star, radius)),
                in_optimistic_hz=bool(hz["inner_period"] <= period <= hz["outer_period"]),
            )
            flags = training_flags(signal)
            diagnostics.append(
                dict(
                    iteration=iteration,
                    rank=rank,
                    period_days=period,
                    duration_days=duration,
                    nominal_training_snr=signal["nominal_training_snr"],
                    training_flags=flags,
                    accepted=not flags or not qualified,
                )
            )
            if flags and qualified:
                continue
            accepted = signal
            signals.append(signal)
            for data, keep in [(coarse, coarse_keep), (training, full_keep)]:
                phase = (data.time.to_numpy() - epoch + period / 2) % period - period / 2
                keep &= abs(phase) > duration * 1.25
            break
        if accepted is None or accepted["nominal_training_snr"] < 5:
            break
    return signals, diagnostics


def make_search(qualified=True):
    # Reuse our original freeze-before-holdout and all holdout/physical checks.
    # Replace only the training search loop; its helper receives no holdout.
    source = inspect.getsource(ORIGINAL_SEARCH)
    start = "    for iteration in range(1, max_signals + 1):\n"
    end = "    result.update(\n        signals=signals,\n"
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError("Original search structure changed; review this adapter")
    left, rest = source.split(start, 1)
    _, right = rest.split(end, 1)
    replacement = "    signals, seed_diagnostics = select_training(training, coarse, star, periods, low, high, baseline, max_signals, qualified=qualified)\n"
    source = (
        left + replacement + end + "        training_seed_diagnostics=seed_diagnostics,\n" + right
    )
    namespace = dict(vars(longbaseline), select_training=select_training, qualified=qualified)
    exec(compile(source, "<qualified-training-search>", "exec"), namespace)
    return namespace["search_combined"]
