"""Conditional new-star validation with physical, raw-light-curve injections."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

import injections
import physical_duration_experiment as development
from realistic_injections import make_loader, total_duration

ROOT = Path(__file__).resolve().parents[1]
SUITE = "realistic_duration_assessment"
METHODS = development.METHODS


def selection():
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    targets = pd.read_csv(ROOT / "reports/tables/targets.csv").set_index("tic")
    data = stars.join(targets[["sectors"]], how="inner")
    exclude = [
        232970271,
        352617553,
        378527773,
        219223742,
        397098265,
        150428135,
        448416124,
        408232559,
        282923395,
        22535327,
    ]
    data = data[
        (data.sectors >= 6)
        & data.Rad.between(0.1, 0.4)
        & (data.earth_period_days <= 20)
        & ~data.known_toi_host
        & ~data.known_ctoi_host
        & ~data.index.isin(exclude)
    ]
    rng = np.random.default_rng(202609084)
    tics, groups = [], []
    for lo, hi in [(8, 11), (11, 12.5), (12.5, 14.01)]:
        candidates = data[(data.Tmag >= lo) & (data.Tmag < hi)].sort_index()
        selected = candidates.iloc[rng.permutation(len(candidates))[:2]]
        if len(selected) != 2:
            raise ValueError("A predefined magnitude stratum lacks two stars")
        tics.extend(map(int, selected.index))
        groups.append(
            dict(
                tmag_interval=[lo, hi],
                eligible=len(candidates),
                selected=list(map(int, selected.index)),
            )
        )
    return tics, groups


def worker(case):
    development.SUITE = SUITE
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[case["tic"]]
    injections.load_target = make_loader(case, star)
    return development.worker(case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = ROOT / "reports/experiments/realistic_duration"
    out.mkdir(parents=True, exist_ok=True)
    prior = json.loads((ROOT / "reports/experiments/physical_duration/plan.json").read_text())
    files = list(prior["source_sha256"]) + [
        "docs/EXPERIMENT_REALISTIC_DURATION.md",
        "scripts/realistic_duration_experiment.py",
        "scripts/realistic_injections.py",
        "requirements-experiments.txt",
    ]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    for name, digest in prior["source_sha256"].items():
        if hashes[name] != digest:
            raise ValueError("The original duration method or benchmark changed")
    path = out / "plan.json"
    if path.exists():
        plan = json.loads(path.read_text())
        if plan["source_sha256"] != hashes:
            raise ValueError("Preserve the frozen follow-up; source or protocol changed")
    else:
        tics, groups = selection()
        base = injections.make_plan(tics, 202609084)
        if len(base) != 54:
            raise ValueError("Selected stars did not support all planned cases")
        stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
        for case in base:
            radius = {0.8: 0.6, 1.0: 0.8, 1.5: 1.0}[case["radius_earth"]]
            orbit = int(case["id"].split("_orbit")[1].split("_")[0])
            star = stars.loc[case["tic"]]
            case.update(
                radius_earth=radius,
                depth=float((radius * 0.0091577 / star.Rad) ** 2),
                impact_parameter=[0.2, 0.55, 0.85][orbit],
                limb_darkening=[[0.2, 0.2], [0.4, 0.2], [0.6, 0.1]][orbit],
                paired_id=case["id"].split("_radius")[0] + f"_radius{radius:g}",
                null_diagnostic=False,
                injection_model="batman quadratic limb darkening; circular orbit; seven-point 120-second exposure integration before our processing",
            )
            case["duration_days"] = total_duration(case, star)
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
        input_files = [
            str(p.relative_to(ROOT))
            for tic in tics
            for p in sorted((ROOT / "data/lightcurves" / str(tic)).glob("*_lc.fits"))
        ]
        plan = dict(
            frozen_utc=datetime.now(timezone.utc).isoformat(),
            seed=202609084,
            selected_tics=tics,
            selection_groups=groups,
            source_sha256=hashes,
            cases=cases,
            telescope_inputs_sha256={
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in input_files
            },
            catalogue_sha256={
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                for p in ["data/catalogs/all_hz_targets.csv", "reports/tables/targets.csv"]
            },
            packages={
                p: importlib.metadata.version(p)
                for p in ["batman-package", "setuptools", "numpy", "astropy"]
            },
            scope="New-star method assessment conditional on development gate; not a planet or novelty claim.",
            duration_config_note=prior["duration_config_note"],
        )
        path.write_text(json.dumps(plan, indent=2) + "\n")
    print(
        json.dumps(dict(prepared_cases=len(plan["cases"]), selected_tics=plan["selected_tics"])),
        flush=True,
    )
    if args.prepare_only:
        return
    if not json.loads((ROOT / "reports/experiments/physical_duration/results.json").read_text())[
        "development_gate_passed"
    ]:
        raise ValueError("The development gate failed; do not execute this follow-up")
    for name, digest in plan["telescope_inputs_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Input changed: {name}")
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
        assessment_gate_passed=gate,
    )
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
