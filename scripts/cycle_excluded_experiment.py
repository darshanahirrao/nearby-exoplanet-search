"""Paired raw injection and recovery benchmark; no production search mutations."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from cycle_excluded import PRODUCTION_CLEAN, clean_cycles, weak_harmonic
import injections
import longbaseline
from parallel_bls import ParallelBoxLeastSquares
from physics import central_duration
import variability

ROOT = Path(__file__).resolve().parents[1]
SUITE = "cycle_excluded_development"
METHODS = {
    "production_harmonic": PRODUCTION_CLEAN,
    "weak_harmonic": weak_harmonic,
    "cycle_excluded": clean_cycles,
}


def worker(case):
    variability.clean_variability = METHODS[case["method"]]
    longbaseline.BoxLeastSquares = ParallelBoxLeastSquares
    result = injections.experiment(case)
    folder = ROOT / "results" / SUITE / case["id"]
    frozen = folder / "frozen_search.json"
    fits = json.loads(frozen.read_text())["signals"] if frozen.exists() else []
    compact = dict(
        id=case["id"],
        paired_id=case["paired_id"],
        method=case["method"],
        tic=case["tic"],
        null_diagnostic=case["null_diagnostic"],
        status=result["status"],
        recovered=bool(result.get("recovered_in_search")) if not case["null_diagnostic"] else None,
        strict=bool(result.get("recovered_with_strict_holdout"))
        if not case["null_diagnostic"]
        else None,
        unflagged_fits=sum(not s["screening_flags"] for s in fits),
        sectors_corrected=sum(
            r.get("applied", False) for r in result.get("variability_models", [])
        ),
        result_path=str((folder / "result.json").relative_to(ROOT)),
        result_sha256=hashlib.sha256((folder / "result.json").read_bytes()).hexdigest(),
        elapsed_seconds=result.get("elapsed_seconds"),
        error=result.get("error"),
    )
    return compact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = ROOT / "reports/experiments/cycle_excluded"
    out.mkdir(parents=True, exist_ok=True)
    source_files = ["docs/EXPERIMENT_CYCLE_EXCLUDED.md"] + [
        "scripts/" + name
        for name in [
            "cycle_excluded.py",
            "cycle_excluded_experiment.py",
            "injections.py",
            "search.py",
            "physics.py",
            "longbaseline.py",
            "parallel_bls.py",
            "variability.py",
        ]
    ]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files}
    plan_path = out / "plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        if plan["source_sha256"] != hashes:
            raise ValueError("Code or protocol changed; preserve the original experiment")
    else:
        seed = 202609078
        cases = injections.make_plan([232970271, 352617553, 378527773], seed)
        if len(cases) != 27 or {c["tic"] for c in cases} != {232970271, 352617553, 378527773}:
            raise ValueError("The predefined stars did not support all 27 injection cases")
        stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
        base = []
        for case in cases:
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
            base.append(case)
        for tic in sorted({c["tic"] for c in base}):
            case = next(c for c in base if c["tic"] == tic).copy()
            case.update(
                depth=0.0, radius_earth=0.0, paired_id=f"{tic}_unmodified", null_diagnostic=True
            )
            base.append(case)
        expanded = []
        for case in base:
            for method in METHODS:
                expanded.append(
                    dict(
                        case,
                        id=method + "__" + case["paired_id"],
                        method=method,
                        suite=SUITE,
                        use_variability_model=True,
                        use_longbaseline=True,
                    )
                )
        plan = dict(
            frozen_utc=datetime.now(timezone.utc).isoformat(),
            seed=seed,
            source_sha256=hashes,
            cases=expanded,
            claims="Synthetic development experiment; no discovery or novelty established.",
        )
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, case): case for case in plan["cases"]}
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
