"""Guarded development comparison of local and leave-one-event-out rankings."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

import cycle_excluded_experiment as benchmark
import injections
import longbaseline
from multimode_cycle_experiment import weak
from realistic_injections import make_loader
from repeated_search import make_repeated_search

ROOT = Path(__file__).resolve().parents[1]
SUITE = "repeated_event_development"
METHODS = {"local_total": "total_snr", "leave_one_out": "leave_one_out_snr"}
BASELINES = ["coarse_only", "qualified_seeds"]
SMOKE = ["233738219_orbit2_radius1", "229614158_orbit0_radius1", "328799321_orbit1_radius1"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(case):
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[case["tic"]]
    injections.load_target = make_loader(case, star)
    benchmark.SUITE = SUITE
    benchmark.METHODS = {name: weak for name in METHODS}
    longbaseline.search_combined = make_repeated_search(METHODS[case["method"]])
    row = benchmark.worker(case)
    row["model_fits_applied"] = row.pop("sectors_corrected")
    path = ROOT / row["result_path"]
    raw = json.loads(path.read_text())
    fits = (
        json.loads((path.parent / "frozen_search.json").read_text())["signals"]
        if row["status"] == "finished"
        else []
    )
    row["strict_and_all_screening_checks"] = (
        bool(
            row["strict"]
            and any(
                not s["screening_flags"]
                and any(
                    abs(s["period_days"] - m["period_days"]) < 1e-10 for m in raw.get("matches", [])
                )
                for s in fits
            )
        )
        if not case["null_diagnostic"]
        else None
    )
    frozen = (
        json.loads((path.parent / "frozen_training.json").read_text())
        if row["status"] == "finished"
        else {}
    )
    row["training_refinements"] = len(frozen.get("training_seed_diagnostics", []))
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    folder = ROOT / "reports/experiments/repeated_events"
    folder.mkdir(exist_ok=True)
    source = ROOT / "reports/experiments/pipeline_confirmation"
    previous = json.loads((source / "plan.json").read_text())
    references = [
        r
        for r in json.loads((source / "results.json").read_text())["rows"]
        if r["method"] in BASELINES
    ]
    hashes = {
        **previous["source_sha256"],
        **previous["catalogue_sha256"],
        **previous["telescope_inputs_sha256"],
    }
    for name, digest in hashes.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Frozen comparison changed: {name}")
    for row in references:
        if sha(ROOT / row["result_path"]) != row["result_sha256"]:
            raise ValueError("Baseline result changed")
    for name in [
        "scripts/repeated_search_experiment.py",
        "scripts/repeated_search.py",
        "scripts/repeated_events.py",
        "docs/EXPERIMENT_REPEATED_EVENTS.md",
        "reports/experiments/period_rank_diagnostic/results.json",
    ]:
        hashes[name] = sha(ROOT / name)
    base = [c for c in previous["cases"] if c["method"] == "coarse_only"]
    cases = [
        dict(c, id=name + "__" + c["paired_id"], method=name, suite=SUITE)
        for c in base
        for name in METHODS
    ]
    if len(cases) != 120:
        raise ValueError("Expected 120 planned new cases")
    spec = dict(
        source_sha256=hashes,
        cases=cases,
        reused_reference_rows=references,
        smoke_paired_ids=SMOKE,
        maximum_distinct_coarse_seeds=4096,
        maximum_fine_fits_per_retained_signal=128,
        maximum_retained_signals=2,
        scope="Previously exposed physical injections, used for method development. No independent validation or planet discovery.",
    )
    plan_path = folder / "plan.json"
    if plan_path.exists():
        old = json.loads(plan_path.read_text())
        if any(old[k] != v for k, v in spec.items()):
            raise ValueError("Preserve the fixed repeated-event experiment")
    else:
        plan_path.write_text(
            json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec), indent=2)
            + "\n"
        )

    def execute(selected, output_name):
        rows = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(worker, c) for c in selected]
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                (folder / "progress.json").write_text(
                    json.dumps(
                        dict(
                            stage=output_name, completed=len(rows), total=len(selected), rows=rows
                        ),
                        indent=2,
                    )
                    + "\n"
                )
                print(json.dumps(row), flush=True)
        return rows

    smoke_rows = execute([c for c in cases if c["paired_id"] in SMOKE], "smoke")
    smoke_gates = {}
    for method in METHODS:
        group = {r["paired_id"]: r for r in smoke_rows if r["method"] == method}
        smoke_gates[method] = bool(
            all(r["status"] == "finished" for r in group.values())
            and group[SMOKE[2]]["strict_and_all_screening_checks"]
            and any(group[k]["strict_and_all_screening_checks"] for k in SMOKE[:2])
        )
    smoke = dict(
        rows=smoke_rows,
        smoke_gates=smoke_gates,
        full_comparison_allowed=any(smoke_gates.values()),
        scope="Selected-case development guard; not an adoption gate or independent recovery claim.",
    )
    (folder / "smoke_results.json").write_text(json.dumps(smoke, indent=2) + "\n")
    print(json.dumps({k: v for k, v in smoke.items() if k != "rows"}), flush=True)
    if not args.full or not smoke["full_comparison_allowed"]:
        return
    rows = execute(cases, "full")
    all_rows = references + rows
    counts = {}
    for method in BASELINES + list(METHODS):
        group = [r for r in all_rows if r["method"] == method]
        counts[method] = dict(
            recovered=sum(r["recovered"] is True for r in group),
            strict=sum(r["strict"] is True for r in group),
            strict_and_all_screening_checks=sum(
                r["strict_and_all_screening_checks"] is True for r in group
            ),
            unmodified_unflagged=sum(r["unflagged_fits"] for r in group if r["null_diagnostic"]),
        )
    paired = {
        method: {
            r["paired_id"]: r
            for r in all_rows
            if r["method"] == method and not r["null_diagnostic"]
        }
        for method in counts
    }
    errors = [r for r in all_rows if r["status"] != "finished"]
    stronger = max(BASELINES, key=lambda m: counts[m]["strict"])
    gates = {}
    for method in METHODS:
        lost = {
            m: [k for k, r in paired[m].items() if r["strict"] and not paired[method][k]["strict"]]
            for m in BASELINES
        }
        gains = [
            k
            for k, r in paired[method].items()
            if r["strict"] and not paired[stronger][k]["strict"]
        ]
        stars = sorted({paired[method][k]["tic"] for k in gains})
        passed = bool(
            not errors
            and not any(lost.values())
            and counts[method]["strict"] >= counts[stronger]["strict"] + 2
            and counts[method]["strict_and_all_screening_checks"]
            >= max(counts[m]["strict_and_all_screening_checks"] for m in BASELINES)
            and counts[method]["unmodified_unflagged"] <= counts[stronger]["unmodified_unflagged"]
            and len(stars) >= 2
        )
        gates[method] = dict(passed=passed, lost_strict=lost, gains=gains, stars_with_gains=stars)
    passing = [m for m in METHODS if gates[m]["passed"]]
    selected = (
        max(
            passing,
            key=lambda m: (
                counts[m]["strict_and_all_screening_checks"],
                counts[m]["strict"],
                m == "local_total",
            ),
        )
        if passing
        else None
    )
    report = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        new_runs=120,
        reused_runs=len(references),
        rows=all_rows,
        counts=counts,
        errors=errors,
        gates=gates,
        development_gate_passed=bool(passing),
        selected_for_fresh_assessment=selected,
    )
    (folder / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
