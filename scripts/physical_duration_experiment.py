"""Fresh paired raw-injection benchmark for an early transit-duration prior."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import partial
import hashlib
import json
from pathlib import Path

import pandas as pd

import cycle_excluded_experiment as benchmark
from cycle_excluded import PRODUCTION_CLEAN
import injections
from multimode_cycle_experiment import weak
from parallel_bls import ParallelBoxLeastSquares
from physical_duration import PhysicalDurationBLS
from physics import central_duration

ROOT = Path(__file__).resolve().parents[1]
SUITE = "physical_duration_development"
METHODS = ["production", "harmonic_three", "physical_duration"]


def worker(case):
    benchmark.SUITE = SUITE
    benchmark.METHODS = dict(
        production=PRODUCTION_CLEAN, harmonic_three=weak, physical_duration=weak
    )
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[case["tic"]]
    benchmark.ParallelBoxLeastSquares = (
        partial(PhysicalDurationBLS, star=star)
        if case["method"] == "physical_duration"
        else ParallelBoxLeastSquares
    )
    row = benchmark.worker(case)
    row["model_fits_applied"] = row.pop("sectors_corrected")
    result_path = ROOT / row["result_path"]
    result = json.loads(result_path.read_text())
    fits = (
        json.loads((result_path.parent / "frozen_search.json").read_text())["signals"]
        if result["status"] == "finished"
        else []
    )
    row["strict_and_all_screening_checks"] = (
        bool(
            row["strict"]
            and any(
                not s["screening_flags"]
                and any(
                    abs(s["period_days"] - m["period_days"]) < 1e-10
                    for m in result.get("matches", [])
                )
                for s in fits
            )
        )
        if not case["null_diagnostic"]
        else None
    )
    row["actual_duration_adapter"] = (
        "physical_duration.py" if case["method"] == "physical_duration" else None
    )
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = ROOT / "reports/experiments/physical_duration"
    out.mkdir(parents=True, exist_ok=True)
    files = ["docs/EXPERIMENT_PHYSICAL_DURATION.md"] + [
        "scripts/" + p
        for p in [
            "physical_duration.py",
            "physical_duration_experiment.py",
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
            raise ValueError("Preserve the frozen experiment; source or protocol changed")
    else:
        seed = 202609083
        tics = [232970271, 352617553, 378527773, 219223742, 397098265]
        base = injections.make_plan(tics, seed)
        if len(base) != 45:
            raise ValueError("The five stars did not support all planned injections")
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
        for tic in tics:
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
            scope="Synthetic development benchmark; no discovery or novelty established.",
            duration_config_note="For physical_duration cases the adapter's band-dependent durations replace the legacy duration field in frozen search config. All other fields and holdout checks remain unchanged.",
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
            strict_and_all_screening_checks=sum(
                r["strict_and_all_screening_checks"] is True for r in rows if r["method"] == m
            ),
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
            if r["strict"] and not paired["physical_duration"][k]["strict"]
        ]
        for m in METHODS[:2]
    }
    errors = [r for r in rows if r["status"] != "finished"]
    gate = bool(
        not errors
        and counts["physical_duration"]["strict"]
        >= max(counts[m]["strict"] for m in METHODS[:2]) + 2
        and not any(lost.values())
        and counts["physical_duration"]["unmodified_unflagged"]
        <= counts["harmonic_three"]["unmodified_unflagged"]
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
