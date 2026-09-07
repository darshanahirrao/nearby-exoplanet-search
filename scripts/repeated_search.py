"""Experimental training-only ranking of a bounded list of refined event models."""

import numpy as np

from parallel_bls import ParallelBoxLeastSquares
from physical_duration import PhysicalDurationBLS
from physics import central_duration, stellar_hz
from qualified_seeds import make_search, training_flags
from repeated_events import EventContrasts, distinct_peaks
from search import event_checks

MAX_REFINED = 128


def select_training(
    training,
    coarse,
    star,
    periods,
    low,
    high,
    baseline,
    max_signals,
    qualified=True,
    metric="leave_one_out_snr",
):
    if metric not in ["total_snr", "leave_one_out_snr"]:
        raise ValueError("Unknown fixed ranking metric")
    hz = stellar_hz(star)
    coarse_keep = np.ones(len(coarse), dtype=bool)
    full_keep = np.ones(len(training), dtype=bool)
    signals, diagnostics = [], []
    for iteration in range(1, max_signals + 1):
        current = training.iloc[np.flatnonzero(full_keep)]
        contrast = EventContrasts(current)
        model = PhysicalDurationBLS(
            coarse.time.to_numpy()[coarse_keep],
            coarse.flux.to_numpy()[coarse_keep],
            coarse.err.to_numpy()[coarse_keep],
            star=star,
        )
        power = model.power(periods, [0.04], objective="likelihood", oversample=5)
        peaks = distinct_peaks(power, baseline, hz["inner_period"], hz["outer_period"])
        seeds = []
        for rank, k in enumerate(peaks, 1):
            score = contrast.measure(
                float(power.period[k]), float(power.transit_time[k]), float(power.duration[k])
            )
            if score["n_events"] >= 3 and score[metric] is not None:
                seeds.append(dict(index=k, global_rank=rank, score=score[metric], **score))
        seeds.sort(key=lambda r: (-r["score"], r["global_rank"]))
        fine_model = ParallelBoxLeastSquares(
            current.time.to_numpy(), current.flux.to_numpy(), current.err.to_numpy()
        )
        accepted = []
        for rank, seed in enumerate(seeds[:MAX_REFINED], 1):
            k = seed["index"]
            p0, duration0 = float(power.period[k]), float(power.duration[k])
            step = periods[min(k + 1, len(periods) - 1)] - periods[max(0, k - 1)]
            fine = np.linspace(max(low, p0 - 2 * step), min(high, p0 + 2 * step), 301)
            expected = central_duration(p0, star)
            durations = np.unique(
                np.clip(
                    np.r_[
                        duration0 * np.array([0.5, 0.75, 1]),
                        expected * np.array([0.5, 0.7, 1, 1.3]),
                    ],
                    0.015,
                    0.3,
                )
            )
            fitted = fine_model.power(fine, durations, objective="likelihood", oversample=15)
            best = int(np.argmax(fitted.power))
            p, epoch, duration, depth = (
                float(fitted[name][best])
                for name in ["period", "transit_time", "duration", "depth"]
            )
            radius = float(np.sqrt(max(0, depth)) * float(star.Rad) / 0.0091577)
            a = (float(star.Mass) * (p / 365.256) ** 2) ** (1 / 3)
            measure = contrast.measure(p, epoch, duration)
            signal = dict(
                seed_iteration=iteration,
                training_peak_rank=rank,
                global_peak_rank=seed["global_rank"],
                period_days=p,
                epoch_btjd=epoch,
                duration_days=duration,
                depth=depth,
                radius_earth_estimate=radius,
                irradiation_earth_estimate=hz["luminosity"] / a**2,
                nominal_training_snr=float(fitted.depth_snr[best]),
                coarse_snr=float(power.depth_snr[k]),
                discovery=event_checks(current, p, epoch, duration),
                central_circular_duration_days=float(central_duration(p, star, radius)),
                in_optimistic_hz=bool(hz["inner_period"] <= p <= hz["outer_period"]),
                event_ranking=measure,
                ranking_metric=metric,
            )
            flags = training_flags(signal)
            usable = not flags and measure[metric] is not None and np.isfinite(measure[metric])
            diagnostics.append(
                dict(
                    iteration=iteration,
                    rank=rank,
                    global_rank=seed["global_rank"],
                    coarse_period_days=p0,
                    coarse_ranking_score=seed["score"],
                    period_days=p,
                    duration_days=duration,
                    nominal_training_snr=signal["nominal_training_snr"],
                    event_ranking=measure,
                    training_flags=flags,
                    eligible=bool(usable),
                    accepted=False,
                )
            )
            if usable:
                accepted.append((signal, len(diagnostics) - 1))
        if not accepted:
            break
        signal, index = max(
            accepted,
            key=lambda item: (item[0]["event_ranking"][metric], -item[0]["training_peak_rank"]),
        )
        diagnostics[index]["accepted"] = True
        signals.append(signal)
        for data, keep in [(coarse, coarse_keep), (training, full_keep)]:
            phase = (
                data.time.to_numpy() - signal["epoch_btjd"] + signal["period_days"] / 2
            ) % signal["period_days"] - signal["period_days"] / 2
            keep &= abs(phase) > signal["duration_days"] * 1.25
    return signals, diagnostics


def make_repeated_search(metric="leave_one_out_snr"):
    adapted = make_search(qualified=True)

    def selector(*args, **kwargs):
        return select_training(*args, **kwargs, metric=metric)

    adapted.__globals__["select_training"] = selector
    return adapted
