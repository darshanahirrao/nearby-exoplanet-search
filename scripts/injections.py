"""Explicitly labelled box-transit recovery experiments in real telescope data.

These measure a limited screening sensitivity, not survey completeness or planet
validation. Box shapes favor BLS; limb darkening and astrophysical validation are
not simulated. All input FITS originals remain unchanged.
"""

from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse, json, time
import hashlib
import numpy as np
import pandas as pd
from search import ROOT, load_target, split_campaigns, scan, event_checks
from physics import stellar_hz, central_duration


def experiment(case):
    start = time.monotonic()
    tic = case["tic"]
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[tic]
    out = ROOT / "results" / case.get("suite", "injections") / case["id"]
    out.mkdir(parents=True, exist_ok=True)
    if (out / "result.json").exists():
        return json.loads((out / "result.json").read_text())
    r = dict(
        case,
        claim="SYNTHETIC INJECTION: not an astrophysical discovery",
        started_utc=datetime.now(timezone.utc).isoformat(),
    )
    try:
        injected = {
            "period": case["period_days"],
            "epoch": case["epoch_btjd"],
            "depth": case["depth"],
            "duration": case["duration_days"],
        }
        df, _ = load_target(tic, inject=injected)
        if case.get("use_variability_model"):
            from variability import clean_variability

            df, records = clean_variability(df, star)
            r["variability_models"] = records
        if case.get("use_longbaseline"):
            from longbaseline import sector_split, search_combined

            dis, val = sector_split(df)
            method = "all_seasons_with_reserved_whole_sectors"
            combined = search_combined(df, star, out)
            signals, config = combined["signals"], combined.get("search_config", {})
            r["training_sectors"] = combined["training_sectors"]
            r["holdout_sectors"] = combined["holdout_sectors"]
        else:
            dis, val, method = split_campaigns(df)
            hz = stellar_hz(star)
            signals, config = scan(
                dis,
                max(1, 0.85 * hz["inner_period"]),
                min(100, 1.15 * hz["outer_period"]),
                star,
                max_signals=3,
            )
        (out / "frozen_search.json").write_text(
            json.dumps(
                dict(
                    signals=signals,
                    config=config,
                    frozen_utc=datetime.now(timezone.utc).isoformat(),
                ),
                indent=2,
            )
        )
        if case.get("use_timing_refinement"):
            from refine import refine_signals

            refined = refine_signals(df, star, signals, out / "timing_refinement")
            signals = refined["signals"]
            r["refinement_split_method"] = refined["split_method"]
        matches = []
        for s in signals:
            p = s["period_days"]
            epoch = s["epoch_btjd"]
            truep = case["period_days"]
            # Require same period (not a harmonic) and overlapping predicted transits
            # at both ends of discovery observations, not just one accidental event.
            drift = []
            for t in [dis.time.min(), dis.time.max()]:
                center = epoch + round((t - epoch) / p) * p
                distance = abs((center - case["epoch_btjd"] + truep / 2) % truep - truep / 2)
                drift.append(float(distance))
            if abs(p / truep - 1) < 0.01 and max(drift) < case["duration_days"] * 0.75:
                hold = (
                    s["holdout"]
                    if case.get("use_timing_refinement") or case.get("use_longbaseline")
                    else event_checks(val, p, epoch, s["duration_days"])
                )
                matches.append(
                    dict(
                        period_days=p,
                        epoch_btjd=epoch,
                        nominal_snr=s.get("nominal_bls_snr", s.get("nominal_training_snr")),
                        discovery_events=s.get(
                            "n_observed_events", s.get("discovery", {}).get("n_observed_events")
                        ),
                        holdout=hold,
                        edge_timing_errors_days=drift,
                    )
                )
        r.update(
            status="finished",
            config=config,
            split_method=method,
            matches=matches,
            recovered_in_search=bool(matches),
            recovered_in_top3=bool(matches) if not case.get("use_longbaseline") else None,
            maximum_trial_fits=2 if case.get("use_longbaseline") else 3,
            recovered_with_strict_holdout=any(
                m["nominal_snr"] >= 7
                and m["discovery_events"] >= 3
                and m["holdout"]["n_observed_events"] >= 2
                and (m["holdout"]["fixed_ephemeris_snr"] or 0) >= 5
                for m in matches
            ),
        )
    except Exception as exc:
        r.update(status="error", error=repr(exc))
    r["elapsed_seconds"] = time.monotonic() - start
    r["code_sha256"] = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in [
            "injections.py",
            "search.py",
            "physics.py",
            "refine.py",
            "variability.py",
            "longbaseline.py",
        ]
    }
    (out / "result.json").write_text(json.dumps(r, indent=2))
    return r


def make_plan(tics, seed):
    rng = np.random.default_rng(seed)
    rows = []
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    for tic in tics:
        star = stars.loc[tic]
        hz = stellar_hz(star)
        df, _ = load_target(tic)
        dis, val, _ = split_campaigns(df)
        low = hz["inner_period"] * 1.08
        high = min(hz["outer_period"] * 0.9, np.ptp(dis.time) * 0.30, 65)
        if high <= low:
            continue
        # Cross radii with the same periods and phases, making size comparisons fair.
        for orbit in range(3):
            period = float(np.exp(rng.uniform(np.log(low), np.log(high))))
            epoch = float(dis.time.min() + rng.uniform(0.05, 1) * period)
            for radius in [0.8, 1.0, 1.5]:
                duration = float(central_duration(period, star, radius) * np.sqrt(1 - 0.5**2))
                rows.append(
                    dict(
                        id=f"{tic}_orbit{orbit}_radius{radius:g}",
                        tic=tic,
                        seed=seed,
                        period_days=period,
                        epoch_btjd=epoch,
                        radius_earth=radius,
                        depth=float((radius * 0.0091577 / star.Rad) ** 2),
                        duration_days=duration,
                        injection_model="box before binning/detrending; approximate impact parameter 0.5",
                    )
                )
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tics", type=int, nargs="+", required=True)
    p.add_argument("--seed", type=int, default=20260907)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--refine", action="store_true")
    p.add_argument("--clean", action="store_true")
    p.add_argument("--longbaseline", action="store_true")
    p.add_argument("--suite", default="injections")
    a = p.parse_args()
    if a.longbaseline and a.refine:
        raise ValueError("--longbaseline and --refine select different search methods")
    if a.suite != Path(a.suite).name:
        raise ValueError("suite must be a plain directory name")
    folder = ROOT / "results" / a.suite
    folder.mkdir(parents=True, exist_ok=True)
    planpath = folder / "plan.json"
    if planpath.exists():
        plan = json.loads(planpath.read_text())["cases"]
        if plan and (
            plan[0]["seed"] != a.seed
            or set(c["tic"] for c in plan) != set(a.tics)
            or bool(plan[0].get("use_timing_refinement")) != a.refine
            or bool(plan[0].get("use_variability_model")) != a.clean
            or bool(plan[0].get("use_longbaseline")) != a.longbaseline
        ):
            raise ValueError(
                "Existing suite has a different plan; select a new --suite name to preserve prior experiments."
            )
    else:
        plan = make_plan(a.tics, a.seed)
        for case in plan:
            case.update(
                suite=a.suite,
                use_timing_refinement=a.refine,
                use_variability_model=a.clean,
                use_longbaseline=a.longbaseline,
            )
        planpath.write_text(
            json.dumps(
                dict(
                    created_utc=datetime.now(timezone.utc).isoformat(),
                    cases=plan,
                    limitations="Small selected sample; box shapes favor BLS; not survey completeness.",
                ),
                indent=2,
            )
        )
    print("BEGIN", datetime.now(timezone.utc).isoformat(), "cases", len(plan), flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        jobs = [pool.submit(experiment, c) for c in plan]
        for job in as_completed(jobs):
            r = job.result()
            results.append(r)
            print(
                r["id"],
                r["status"],
                "recovered",
                r.get("recovered_in_search", r.get("recovered_in_top3")),
                "holdout",
                r.get("recovered_with_strict_holdout"),
                round(r["elapsed_seconds"], 1),
                r.get("error", ""),
                flush=True,
            )
            (folder / "summary.json").write_text(
                json.dumps(
                    dict(updated_utc=datetime.now(timezone.utc).isoformat(), results=results),
                    indent=2,
                )
            )
    print(
        "END",
        len(results),
        "recovered",
        sum(r.get("recovered_in_search", r.get("recovered_in_top3", False)) for r in results),
        "strict_holdout",
        sum(r.get("recovered_with_strict_holdout", False) for r in results),
        flush=True,
    )


if __name__ == "__main__":
    main()
