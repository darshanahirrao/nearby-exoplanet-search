"""Search multiple seasons together while reserving complete observing sectors.

Thirty-minute bins accelerate the coarse BLS search. Original ten-minute samples
refine the fit. This is an additional exploratory search, not an independent survey
or a calibrated discovery probability. Whole-sector holdouts avoid sharing the
sector-local detrending/variability fits across training and test observations.
"""

from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import hashlib
import json
import time
import numpy as np
import pandas as pd
from astropy.timeseries import BoxLeastSquares
from search import ROOT, bin_series, event_checks, known_matches
from physics import stellar_hz, central_duration
from variability import clean_variability


def sector_split(df):
    sectors = np.sort(df.sector.unique())
    if len(sectors) < 3:
        return df.copy(), df.iloc[:0].copy()
    reserved = sectors[1::3]
    return df[~df.sector.isin(reserved)].copy(), df[df.sector.isin(reserved)].copy()


def search_combined(df, star, output_folder):
    training, holdout = sector_split(df)
    hz = stellar_hz(star)
    start = time.monotonic()
    result = dict(
        training_sectors=sorted(map(int, training.sector.unique())),
        holdout_sectors=sorted(map(int, holdout.sector.unique())),
        training_points=len(training),
        holdout_points=len(holdout),
        claims="Exploratory fits only. No new or validated planet claimed.",
    )
    if len(holdout) == 0:
        return dict(result, status="skipped_fewer_than_three_sectors", signals=[])
    low = max(1, 0.85 * hz["inner_period"])
    high = min(100, 1.15 * hz["outer_period"], 0.48 * np.ptp(training.time))
    if low >= high:
        return dict(result, status="skipped_no_period_range", signals=[])
    coarse = []
    for sector, part in training.groupby("sector"):
        t, y, e = bin_series(
            part.time.to_numpy(), part.flux.to_numpy(), part.err.to_numpy(), step=30 / 1440
        )
        coarse.append(pd.DataFrame(dict(time=t, flux=y, err=e, sector=sector)))
    coarse = pd.concat(coarse).sort_values("time")
    durations = np.array([0.04, 0.06, 0.09, 0.13, 0.18, 0.25])
    baseline = float(np.ptp(training.time))
    count = max(3000, int(np.ceil(np.log(high / low) * 3 * baseline / durations.min())) + 1)
    periods = np.geomspace(low, high, count)
    coarse_keep = np.ones(len(coarse), dtype=bool)
    full_keep = np.ones(len(training), dtype=bool)
    signals = []
    for iteration in range(1, 3):
        model = BoxLeastSquares(
            coarse.time.to_numpy()[coarse_keep],
            coarse.flux.to_numpy()[coarse_keep],
            coarse.err.to_numpy()[coarse_keep],
        )
        power = model.power(periods, durations, objective="likelihood", oversample=5)
        k = int(np.argmax(power.power))
        p0 = float(power.period[k])
        duration0 = float(power.duration[k])
        step = periods[min(k + 1, len(periods) - 1)] - periods[max(0, k - 1)]
        fine = np.linspace(max(low, p0 - 2 * step), min(high, p0 + 2 * step), 301)
        expected = central_duration(p0, star)
        fine_durations = np.unique(
            np.clip(
                np.r_[
                    duration0 * np.array([0.5, 0.75, 1]), expected * np.array([0.5, 0.7, 1, 1.3])
                ],
                0.015,
                0.3,
            )
        )
        full = BoxLeastSquares(
            training.time.to_numpy()[full_keep],
            training.flux.to_numpy()[full_keep],
            training.err.to_numpy()[full_keep],
        )
        fitted = full.power(fine, fine_durations, objective="likelihood", oversample=15)
        best = int(np.argmax(fitted.power))
        period = float(fitted.period[best])
        epoch = float(fitted.transit_time[best])
        duration = float(fitted.duration[best])
        depth = float(fitted.depth[best])
        radius = float(np.sqrt(max(0, depth)) * float(star.Rad) / 0.0091577)
        a = (float(star.Mass) * (period / 365.256) ** 2) ** (1 / 3)
        signals.append(
            dict(
                seed_iteration=iteration,
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
        )
        for data, keep in [(coarse, coarse_keep), (training, full_keep)]:
            phase = (data.time.to_numpy() - epoch + period / 2) % period - period / 2
            keep &= abs(phase) > duration * 1.25
        if signals[-1]["nominal_training_snr"] < 5:
            break
    result.update(
        signals=signals,
        search_config=dict(
            minimum_period=low,
            maximum_period=high,
            n_periods=count,
            coarse_bin_minutes=30,
            coarse_durations_days=durations.tolist(),
            baseline_days=baseline,
        ),
        frozen_utc=datetime.now(timezone.utc).isoformat(),
    )
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    (output_folder / "frozen_training.json").write_text(json.dumps(result, indent=2))
    for signal in signals:
        p = signal["period_days"]
        epoch = signal["epoch_btjd"]
        duration = signal["duration_days"]
        signal["holdout"] = event_checks(holdout, p, epoch, duration)
        d = signal["discovery"]
        v = signal["holdout"]
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
        if duration > 1.6 * signal["central_circular_duration_days"]:
            flags.append("long_relative_to_circular_transit")
        if signal["nominal_training_snr"] < 7:
            flags.append("low_nominal_training_snr")
        if v["n_observed_events"] < 2:
            flags.append("insufficient_holdout_events")
        elif (v["fixed_ephemeris_snr"] or 0) < 5:
            flags.append("not_recovered_in_sector_holdout")
        if v["n_observed_events"] >= 2 and v["n_positive_events"] < 0.6 * v["n_observed_events"]:
            flags.append("inconsistent_holdout_depth_signs")
        signal["screening_flags"] = flags
    result.update(status="longbaseline_screened", elapsed_seconds=time.monotonic() - start)
    return result


def process_target(tic, source_tag=""):
    original = ROOT / "results" / (str(tic) + source_tag)
    folder = ROOT / "results" / f"{tic}_longbaseline"
    if (folder / "result.json").exists():
        return json.loads((folder / "result.json").read_text())
    prior = json.loads((original / "result.json").read_text())
    star = pd.Series(prior["star"])
    clean_folder = ROOT / "results" / f"{tic}_variability"
    if not source_tag and (clean_folder / "lightcurve.csv.gz").exists():
        df = pd.read_csv(clean_folder / "lightcurve.csv.gz")
        source = clean_folder / "lightcurve.csv.gz"
    else:
        source = original / "lightcurve.csv.gz"
        df, _ = clean_variability(pd.read_csv(source), star)
    result = search_combined(df, star, folder)
    folder.mkdir(exist_ok=True)
    for s in result["signals"]:
        s["known_matches"] = known_matches(tic, s["period_days"])
        if s["known_matches"]:
            s["screening_flags"].append("known_catalogue_signal_or_harmonic")
    result.update(
        tic=tic,
        star=prior["star"],
        source_data=str(source.relative_to(ROOT)),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (folder / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tics", nargs="+", type=int)
    parser.add_argument("--all-screened", action="store_true")
    parser.add_argument("--source-tag", default="")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    tics = args.tics or []
    if args.all_screened:
        tics += [
            int(p.parent.name)
            for p in (ROOT / "results").glob("*/result.json")
            if p.parent.name.isdigit() and p.parent.name != "150428135"
        ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(process_target, t, args.source_tag): t for t in tics}
        for job in as_completed(jobs):
            try:
                r = job.result()
                print(
                    r["tic"],
                    r["status"],
                    round(r.get("elapsed_seconds", 0), 1),
                    "unflagged",
                    sum(not s["screening_flags"] for s in r["signals"]),
                    flush=True,
                )
            except Exception as exc:
                print(jobs[job], "error", repr(exc), flush=True)


if __name__ == "__main__":
    main()
