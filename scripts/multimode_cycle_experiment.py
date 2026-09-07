"""Fresh paired injections with identical three-mode budgets for all filters."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from cycle_excluded import PRODUCTION_CLEAN, clean_cycles, weak_harmonic
import cycle_excluded_experiment as benchmark
import injections
from physics import central_duration

ROOT = Path(__file__).resolve().parents[1]
SUITE = "multimode_cycle_development"
METHODS = ["production_harmonic", "weak_harmonic", "cycle_excluded"]


def repeated(df, star, method):
    records = []
    for iteration in range(1, 4):
        df, current = method(df, star)
        records.extend(dict(r, mode_pass=iteration) for r in current)
        if not any(r["applied"] for r in current):
            break
    return df, records


def production(df, star):
    return repeated(df, star, PRODUCTION_CLEAN)


def weak(df, star):
    return repeated(df, star, weak_harmonic)


def cycles(df, star):
    return repeated(df, star, clean_cycles)


def worker(case):
    # Set these inside each worker so macOS process spawning preserves the adapter.
    benchmark.SUITE = SUITE
    benchmark.METHODS = dict(
        production_harmonic=production, weak_harmonic=weak, cycle_excluded=cycles
    )
    result = benchmark.worker(case)
    result["model_fits_applied"] = result.pop("sectors_corrected")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = ROOT / "reports/experiments/multimode_cycles"
    out.mkdir(parents=True, exist_ok=True)
    files = ["docs/EXPERIMENT_MULTIMODE_CYCLES.md"] + [
        "scripts/" + p
        for p in [
            "multimode_cycle_experiment.py",
            "cycle_excluded.py",
            "cycle_excluded_experiment.py",
            "injections.py",
            "search.py",
            "variability.py",
            "physics.py",
            "longbaseline.py",
            "parallel_bls.py",
        ]
    ]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    path = out / "plan.json"
    if path.exists():
        plan = json.loads(path.read_text())
        if plan["source_sha256"] != hashes:
            raise ValueError("Preserve the original experiment; source or protocol changed")
    else:
        seed = 202609080
        base = injections.make_plan([232970271, 352617553, 378527773], seed)
        if len(base) != 27:
            raise ValueError("The selected stars did not support all planned injections")
        stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
        for case in base:
            radius = {0.8: 0.6, 1.0: 0.8, 1.5: 1.0}[case["radius_earth"]]
            star = stars.loc[case["tic"]]
            case.update(
                radius_earth=radius,
                depth=float((radius * 0.0091577 / star.Rad) ** 2),
                duration_days=float(
                    central_duration(case["period_days"], star, radius) * 0.75**0.5
                ),
                paired_id=case["id"].split("_radius")[0] + f"_radius{radius:g}",
                null_diagnostic=False,
            )
        for tic in sorted({c["tic"] for c in base}):
            case = next(c for c in base if c["tic"] == tic).copy()
            case.update(
                depth=0.0, radius_earth=0.0, paired_id=f"{tic}_unmodified", null_diagnostic=True
            )
            base.append(case)
        cases = [
            dict(
                c,
                id=m + "__" + c["paired_id"],
                method=m,
                suite=SUITE,
                use_variability_model=True,
                use_longbaseline=True,
            )
            for c in base
            for m in METHODS
        ]
        plan = dict(
            frozen_utc=datetime.now(timezone.utc).isoformat(),
            seed=seed,
            source_sha256=hashes,
            cases=cases,
            maximum_variability_passes=3,
            claims="Synthetic development benchmark. No discovery or novelty established.",
        )
        path.write_text(json.dumps(plan, indent=2) + "\n")
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(worker, c) for c in plan["cases"]]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            (out / "progress.json").write_text(
                json.dumps(dict(completed=len(rows), total=len(futures), rows=rows), indent=2)
                + "\n"
            )
            print(json.dumps(row), flush=True)
    counts = {
        m: dict(
            recovered=sum(r["recovered"] is True for r in rows if r["method"] == m),
            strict=sum(r["strict"] is True for r in rows if r["method"] == m),
            unmodified_unflagged=sum(
                r["unflagged_fits"] for r in rows if r["method"] == m and r["null_diagnostic"]
            ),
        )
        for m in METHODS
    }
    paired = {
        m: {r["paired_id"]: r for r in rows if r["method"] == m and not r["null_diagnostic"]}
        for m in METHODS
    }
    lost = {
        m: [
            k
            for k, r in paired[m].items()
            if r["strict"] and not paired["cycle_excluded"][k]["strict"]
        ]
        for m in ["production_harmonic", "weak_harmonic"]
    }
    errors = [r for r in rows if r["status"] != "finished"]
    gate = bool(
        not errors
        and counts["cycle_excluded"]["strict"] >= max(counts[m]["strict"] for m in lost) + 2
        and not any(lost.values())
        and counts["cycle_excluded"]["unmodified_unflagged"]
        <= counts["weak_harmonic"]["unmodified_unflagged"]
    )
    report = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        rows=rows,
        counts=counts,
        lost_strict_recoveries=lost,
        errors=errors,
        development_gate_passed=gate,
    )
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
