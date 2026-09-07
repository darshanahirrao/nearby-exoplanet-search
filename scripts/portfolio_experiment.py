"""Explicit candidate-capacity development test with equal-budget rankings."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from portfolio_search import make_portfolio_search
import repeated_search_experiment as repeated

ROOT = Path(__file__).resolve().parents[1]
SUITE = "portfolio_development"
METHODS = ["local_total", "leave_one_out"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(case):
    repeated.SUITE = SUITE
    repeated.make_repeated_search = make_portfolio_search
    row = repeated.worker(case)
    path = ROOT / row["result_path"]
    result = json.loads(path.read_text())
    # The reused injection driver has historical two-fit metadata; its matching
    # loop already evaluates all fits. Record the actual adapter's limit here.
    result.update(
        maximum_trial_fits=32,
        search_adapter="portfolio_search.py",
        claims="Synthetic development injection or explicitly unmodified control; no planet discovery.",
    )
    path.write_text(json.dumps(result, indent=2) + "\n")
    row["result_sha256"] = sha(path)
    row["maximum_trial_fits"] = 32
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    folder = ROOT / "reports/experiments/portfolio"
    folder.mkdir(exist_ok=True)
    previous = json.loads((ROOT / "reports/experiments/repeated_events/plan.json").read_text())
    hashes = dict(previous["source_sha256"])
    for name, digest in hashes.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Prior source changed: {name}")
    for name in [
        "scripts/portfolio_search.py",
        "scripts/portfolio_experiment.py",
        "docs/EXPERIMENT_PORTFOLIO.md",
        "reports/experiments/repeated_events/smoke_results.json",
        "reports/experiments/depth_consistency_diagnostic/results.json",
    ]:
        hashes[name] = sha(ROOT / name)
    references = [r for r in previous["reused_reference_rows"] if r["method"] == "coarse_only"]
    for row in references:
        if sha(ROOT / row["result_path"]) != row["result_sha256"]:
            raise ValueError("Reference result changed")
    cases = [dict(c, suite=SUITE) for c in previous["cases"]]
    spec = dict(
        source_sha256=hashes,
        cases=cases,
        reused_reference_rows=references,
        smoke_paired_ids=repeated.SMOKE,
        maximum_retained_signals=32,
        maximum_refined_training_fits=128,
        scope=__doc__,
    )
    path = folder / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != v for k, v in spec.items()):
            raise ValueError("Preserve the fixed capacity experiment")
    else:
        path.write_text(
            json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec), indent=2)
            + "\n"
        )

    def execute(selected, stage):
        rows = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(worker, c) for c in selected]
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                (folder / "progress.json").write_text(
                    json.dumps(
                        dict(stage=stage, completed=len(rows), total=len(selected), rows=rows),
                        indent=2,
                    )
                    + "\n"
                )
                print(json.dumps(row), flush=True)
        return rows

    smoke_rows = execute([c for c in cases if c["paired_id"] in repeated.SMOKE], "smoke")
    smoke_gates = {}
    for method in METHODS:
        group = {r["paired_id"]: r for r in smoke_rows if r["method"] == method}
        smoke_gates[method] = bool(
            all(r["status"] == "finished" for r in group.values())
            and group[repeated.SMOKE[2]]["strict_and_all_screening_checks"]
            and any(group[k]["strict_and_all_screening_checks"] for k in repeated.SMOKE[:2])
        )
    smoke = dict(
        rows=smoke_rows,
        smoke_gates=smoke_gates,
        full_comparison_allowed=any(smoke_gates.values()),
        scope="Exposed smoke cases; not independent validation.",
    )
    (folder / "smoke_results.json").write_text(json.dumps(smoke, indent=2) + "\n")
    print(json.dumps({k: v for k, v in smoke.items() if k != "rows"}), flush=True)
    if not args.full or not smoke["full_comparison_allowed"]:
        return
    rows = execute(cases, "full")
    all_rows = references + rows
    counts = {}
    for method in ["coarse_only"] + METHODS:
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
        m: {r["paired_id"]: r for r in all_rows if r["method"] == m and not r["null_diagnostic"]}
        for m in counts
    }
    errors = [r for r in all_rows if r["status"] != "finished"]
    gates = {}
    for method in METHODS:
        lost = [
            k
            for k, r in paired["coarse_only"].items()
            if r["strict"] and not paired[method][k]["strict"]
        ]
        gains = [
            k
            for k, r in paired[method].items()
            if r["strict"] and not paired["coarse_only"][k]["strict"]
        ]
        stars = sorted({paired[method][k]["tic"] for k in gains})
        passed = bool(
            not errors
            and not lost
            and counts[method]["strict"] >= counts["coarse_only"]["strict"] + 2
            and counts[method]["strict_and_all_screening_checks"]
            >= counts["coarse_only"]["strict_and_all_screening_checks"]
            and counts[method]["unmodified_unflagged"]
            <= counts["coarse_only"]["unmodified_unflagged"]
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
    result = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        new_runs=len(rows),
        reused_runs=len(references),
        rows=all_rows,
        counts=counts,
        errors=errors,
        gates=gates,
        development_gate_passed=bool(passing),
        selected_for_fresh_assessment=selected,
    )
    (folder / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
