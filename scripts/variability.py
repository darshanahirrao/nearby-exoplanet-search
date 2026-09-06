"""Conservative sector-local removal of strong, rapid periodic variability.

Exploratory sensitivity pass, not a new astrophysical inference. Each sector is
treated separately, without sharing fitted flux information across holdouts.
Signal injections must precede this operation to test suppression of transits.
"""

from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle
from scipy.optimize import minimize_scalar
from search import ROOT, robust_sigma, split_campaigns, scan, known_matches
from refine import refine_signals
from physics import stellar_hz


def clean_variability(df, star):
    result = df.copy()
    records = []
    hz = stellar_hz(star)
    min_frequency = max(0.5, 2 / hz["inner_period"])
    for sector, data in df.groupby("sector"):
        if len(data) < 300 or np.ptp(data.time) < 2:
            continue
        t = data.time.to_numpy()
        y = data.flux.to_numpy()
        e = data.err.to_numpy()
        t = t - np.median(t)
        ls = LombScargle(t, y, e)
        f, power = ls.autopower(
            minimum_frequency=min_frequency, maximum_frequency=25, samples_per_peak=5
        )
        k = int(np.argmax(power))
        record = dict(sector=int(sector), peak_fractional_power=float(power[k]), applied=False)
        # Require strong variability well above a sparse Earth-sized transit's
        # sinusoidal power; period also lies below half the nominal inner HZ period.
        if power[k] < 0.10:
            records.append(record)
            continue
        step = f[1] - f[0]
        best = minimize_scalar(
            lambda freq: -ls.power(freq),
            bounds=(max(min_frequency, f[k] - step), min(25, f[k] + step)),
            method="bounded",
        )
        frequency = float(best.x)
        columns = [np.ones(len(t))]
        for harmonic in [1, 2, 3]:
            angle = 2 * np.pi * harmonic * frequency * t
            columns += [np.sin(angle), np.cos(angle)]
        design = np.array(columns).T
        keep = np.ones(len(t), dtype=bool)
        for _ in range(4):
            coef = np.linalg.lstsq(design[keep] / e[keep, None], y[keep] / e[keep], rcond=None)[0]
            model = design @ coef
            residual = y - model
            sigma = max(robust_sigma(residual), np.median(e))
            # Protect deep dips and flares from influencing the variability fit.
            keep = (residual > -3 * sigma) & (residual < 3 * sigma)
        corrected = y - model + coef[0]
        corrected = corrected / np.median(corrected)
        result.loc[data.index, "flux"] = corrected
        record.update(
            applied=True,
            period_days=1 / frequency,
            fractional_power=float(-best.fun),
            fit_points=int(keep.sum()),
            original_scatter=float(robust_sigma(y)),
            corrected_scatter=float(robust_sigma(corrected)),
        )
        records.append(record)
    return result, records


def process_target(tic):
    original = ROOT / "results" / str(tic)
    folder = original.with_name(original.name + "_variability")
    if (folder / "result.json").exists():
        return json.loads((folder / "result.json").read_text())
    prior = json.loads((original / "result.json").read_text())
    star = pd.Series(prior["star"])
    source = original / "lightcurve.csv.gz"
    df = pd.read_csv(source)
    clean, records = clean_variability(df, star)
    folder.mkdir(exist_ok=True)
    clean.to_csv(folder / "lightcurve.csv.gz", index=False)
    discovery, _, _ = split_campaigns(clean)
    hz = stellar_hz(star)
    signals, config = scan(
        discovery, max(1, 0.85 * hz["inner_period"]), min(100, 1.15 * hz["outer_period"]), star
    )
    (folder / "frozen_discovery.json").write_text(
        json.dumps(
            dict(signals=signals, config=config, frozen_utc=datetime.now(timezone.utc).isoformat()),
            indent=2,
        )
    )
    result = refine_signals(clean, star, signals, folder)
    for signal in result["signals"]:
        signal["known_matches"] = known_matches(tic, signal["period_days"])
        if signal["known_matches"]:
            signal["screening_flags"].append("known_catalogue_signal_or_harmonic")
    result.update(
        tic=tic,
        status="variability_screened",
        star=prior["star"],
        variability_models=records,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        variability_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        claims="Exploratory signals after variability filtering. No planet validated or discovery claimed.",
    )
    (folder / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tics", type=int, nargs="+")
    parser.add_argument("--all-screened", action="store_true")
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
        jobs = {pool.submit(process_target, tic): tic for tic in tics}
        for job in as_completed(jobs):
            try:
                result = job.result()
                print(
                    result["tic"],
                    "variability_screened",
                    "sectors_cleaned",
                    sum(r["applied"] for r in result["variability_models"]),
                    "unflagged",
                    sum(not s["screening_flags"] for s in result["signals"]),
                    flush=True,
                )
            except Exception as exc:
                print(jobs[job], "error", repr(exc), flush=True)


if __name__ == "__main__":
    main()
