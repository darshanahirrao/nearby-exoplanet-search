"""Three-stage follow-up: discovery, separate timing refinement, then holdout.

Preserves first-pass outputs. All reported S/N values remain nominal. The separate
refinement data improve ephemerides across multi-year gaps; they cannot also serve
as independent confirmation data. Settings must be frozen before a fresh test set.
"""

from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse, json, hashlib
import numpy as np
import pandas as pd
from astropy.timeseries import BoxLeastSquares
from search import ROOT, split_campaigns, event_checks, known_matches
from physics import stellar_hz, central_duration


def three_way_split(df):
    discovery, other, method = split_campaigns(df)
    sectors = np.sort(other.sector.unique())
    if len(sectors) >= 2:
        count = min(3, max(1, len(sectors) // 3))
        chosen = sectors[np.unique(np.linspace(0, len(sectors) - 1, count).astype(int))]
        refinement = other[other.sector.isin(chosen)].copy()
        holdout = other[~other.sector.isin(chosen)].copy()
        note = "Time-refinement sectors chosen at fixed evenly spaced indices from other sectors; remaining sectors held back."
    elif len(other) >= 100:
        cut = float(np.median(other.time))
        refinement = other[other.time < cut - 0.25].copy()
        holdout = other[other.time > cut + 0.25].copy()
        note = "Single remaining sector split at median time, with a 0.5-day guard gap; weaker independence than separate campaigns."
    else:
        refinement = other.iloc[:0].copy()
        holdout = other.copy()
        note = "No separate timing-refinement data available."
    return discovery, refinement, holdout, method + "; " + note


def refine_signals(df, star, signals, outdir=None):
    discovery, timing, holdout, method = three_way_split(df)
    training = pd.concat([discovery, timing]).sort_values("time")
    remaining = np.ones(len(training), dtype=bool)
    fitted = []
    hz = stellar_hz(star)
    for seed in signals:
        p0 = seed["period_days"]
        dur = seed["duration_days"]
        width = 3 * dur * p0 / max(np.ptp(discovery.time), 1.0)
        # Broad enough for discovery-only timing uncertainty, with finer spacing
        # determined by the longer training baseline. Holdout is never in this fit.
        lo = max(0.5, p0 - width)
        hi = p0 + width
        count = max(401, int(np.ceil((hi - lo) * 8 * np.ptp(training.time) / (p0 * dur))))
        periods = np.linspace(lo, hi, count)
        model = BoxLeastSquares(
            training.time.to_numpy()[remaining],
            training.flux.to_numpy()[remaining],
            training.err.to_numpy()[remaining],
        )
        b = model.power(
            periods,
            np.clip(dur * np.array([0.7, 1, 1.3]), 0.015, 0.3),
            objective="likelihood",
            oversample=15,
        )
        k = int(np.argmax(b.power))
        p = float(b.period[k])
        epoch = float(b.transit_time[k])
        duration = float(b.duration[k])
        depth = float(b.depth[k])
        r = {
            "seed_iteration": seed["iteration"],
            "seed_period_days": p0,
            "period_days": p,
            "epoch_btjd": epoch,
            "duration_days": duration,
            "depth": depth,
            "nominal_training_snr": float(b.depth_snr[k]),
            "refinement_period_range_days": [lo, hi],
            "refinement_grid_size": count,
            "discovery": event_checks(discovery, p, epoch, duration),
            "timing_refinement": event_checks(timing, p, epoch, duration),
        }
        r["radius_earth_estimate"] = float(np.sqrt(max(0, depth)) * float(star.Rad) / 0.0091577)
        a = (float(star.Mass) * (p / 365.256) ** 2) ** (1 / 3)
        r["irradiation_earth_estimate"] = hz["luminosity"] / a**2
        r["in_optimistic_hz"] = bool(hz["inner_period"] <= p <= hz["outer_period"])
        r["central_circular_duration_days"] = float(
            central_duration(p, star, r["radius_earth_estimate"])
        )
        fitted.append(r)
        phase = (training.time.to_numpy() - epoch + p / 2) % p - p / 2
        remaining &= abs(phase) > duration * 1.25
    frozen = {
        "signals": fitted,
        "split_method": method,
        "discovery_sectors": sorted(map(int, discovery.sector.unique())),
        "timing_refinement_sectors": sorted(map(int, timing.sector.unique())),
        "holdout_sectors": sorted(map(int, holdout.sector.unique())),
        "points": [len(discovery), len(timing), len(holdout)],
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
    }
    if outdir:
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "frozen_refinement.json").write_text(json.dumps(frozen, indent=2))
    for r in fitted:
        r["holdout"] = event_checks(holdout, r["period_days"], r["epoch_btjd"], r["duration_days"])
        flags = []
        d = r["discovery"]
        v = r["holdout"]
        if d["n_observed_events"] < 3:
            flags.append("fewer_than_three_discovery_events")
        if (d.get("single_event_power_fraction") or 0) > 0.6:
            flags.append("dominated_by_one_discovery_event")
        if (d.get("odd_even_sigma") or 0) > 3:
            flags.append("odd_even_discrepancy")
        if not 0.5 <= r["radius_earth_estimate"] <= 2:
            flags.append("outside_initial_small_planet_radius_range")
        if not r["in_optimistic_hz"]:
            flags.append("outside_nominal_optimistic_hz")
        if r["duration_days"] > 1.6 * r["central_circular_duration_days"]:
            flags.append("long_relative_to_circular_transit")
        if r["nominal_training_snr"] < 7:
            flags.append("low_nominal_training_snr")
        if v["n_observed_events"] < 2:
            flags.append("insufficient_holdout_events")
        elif (v["fixed_ephemeris_snr"] or 0) < 5:
            flags.append("not_recovered_in_final_holdout")
        if v["n_observed_events"] >= 2 and v["n_positive_events"] < 0.6 * v["n_observed_events"]:
            flags.append("inconsistent_holdout_depth_signs")
        r["screening_flags"] = flags
    return frozen


def refine_target(input_folder):
    source = Path(input_folder).resolve()
    original = json.loads((source / "result.json").read_text())
    out = source.with_name(source.name + "_refined")
    if (out / "result.json").exists():
        return json.loads((out / "result.json").read_text())
    df = pd.read_csv(source / "lightcurve.csv.gz")
    star = pd.Series(original["star"])
    tic = original["tic"]
    result = refine_signals(df, star, original["signals"], out)
    for s in result["signals"]:
        s["known_matches"] = known_matches(tic, s["period_days"])
        if s["known_matches"]:
            s["screening_flags"].append("known_catalogue_signal_or_harmonic")
    result.update(
        tic=tic,
        status="refined_screening",
        star=original["star"],
        source_result=str((source / "result.json").relative_to(ROOT)),
        source_result_sha256=hashlib.sha256((source / "result.json").read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        claims="Preliminary screening only; no new or validated planet claim.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--folders", nargs="*")
    p.add_argument("--all-screened", action="store_true")
    p.add_argument("--workers", type=int, default=2)
    a = p.parse_args()
    folders = [Path(x) for x in (a.folders or [])]
    if a.all_screened:
        folders += [
            x.parent
            for x in (ROOT / "results").glob("*/result.json")
            if x.parent.name.isdigit() and x.parent.name != "150428135"
        ]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        jobs = {pool.submit(refine_target, f): f for f in folders}
        for j in as_completed(jobs):
            try:
                r = j.result()
                print(
                    r["tic"],
                    "refined",
                    "signals",
                    len(r["signals"]),
                    "unflagged",
                    sum(not s["screening_flags"] for s in r["signals"]),
                    flush=True,
                )
            except Exception as exc:
                print(jobs[j].name, "error", repr(exc), flush=True)


if __name__ == "__main__":
    main()
