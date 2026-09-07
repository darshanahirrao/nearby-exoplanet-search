"""Retrospective ablation of seed refinement and early training qualification."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import cycle_excluded_experiment as benchmark
import longbaseline
from multimode_cycle_experiment import weak
from parallel_bls import ParallelBoxLeastSquares
from qualified_seeds import make_search

ROOT = Path(__file__).resolve().parents[1]
SUITE = "qualified_seed_development"
NEW_METHODS = ["coarse_only", "qualified_seeds"]
COMPARISONS = ["production", "harmonic_three", "coarse_only"]


def worker(case):
    benchmark.SUITE = SUITE
    benchmark.METHODS = {m: weak for m in NEW_METHODS}
    benchmark.ParallelBoxLeastSquares = ParallelBoxLeastSquares
    longbaseline.search_combined = make_search(qualified=case["method"] == "qualified_seeds")
    row = benchmark.worker(case)
    row["model_fits_applied"] = row.pop("sectors_corrected")
    path = ROOT / row["result_path"]
    result = json.loads(path.read_text())
    fits = (
        json.loads((path.parent / "frozen_search.json").read_text())["signals"]
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
    frozen = (
        json.loads((path.parent / "frozen_training.json").read_text())
        if result["status"] == "finished"
        else {}
    )
    row["training_refinements"] = len(frozen.get("training_seed_diagnostics", []))
    row["actual_search_adapter"] = "qualified_seeds.py"
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = ROOT / "reports/experiments/qualified_seeds"
    out.mkdir(parents=True, exist_ok=True)
    source_plan = ROOT / "reports/experiments/physical_duration/plan.json"
    source_results = ROOT / "reports/experiments/physical_duration/results.json"
    prior = json.loads(source_plan.read_text())
    files = list(prior["source_sha256"]) + [
        "docs/EXPERIMENT_QUALIFIED_SEEDS.md",
        "scripts/qualified_seeds.py",
        "scripts/qualified_seed_experiment.py",
    ]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    for name, digest in prior["source_sha256"].items():
        if hashes[name] != digest:
            raise ValueError("Prior comparison source changed")
    references = [
        r for r in json.loads(source_results.read_text())["rows"] if r["method"] in COMPARISONS[:2]
    ]
    for row in references:
        if (
            hashlib.sha256((ROOT / row["result_path"]).read_bytes()).hexdigest()
            != row["result_sha256"]
        ):
            raise ValueError("Prior comparison result changed")
    path = out / "plan.json"
    if path.exists():
        plan = json.loads(path.read_text())
        if plan["source_sha256"] != hashes:
            raise ValueError("Preserve the frozen ablation; source or protocol changed")
    else:
        base = [c for c in prior["cases"] if c["method"] == "production"]
        cases = [
            dict(c, id=m + "__" + c["paired_id"], method=m, suite=SUITE)
            for c in base
            for m in NEW_METHODS
        ]
        if len(cases) != 100:
            raise ValueError("Expected 100 new runs")
        plan = dict(
            frozen_utc=datetime.now(timezone.utc).isoformat(),
            source_sha256=hashes,
            source_plan_sha256=hashlib.sha256(source_plan.read_bytes()).hexdigest(),
            source_results_sha256=hashlib.sha256(source_results.read_bytes()).hexdigest(),
            cases=cases,
            reused_reference_rows=references,
            maximum_training_refinements_per_retained_signal=64,
            maximum_retained_fits=2,
            scope="Retrospective development ablation, not fresh or independent validation, discovery or novelty.",
            adapter_note="qualified_seeds.py replaces the training loop, applies the physical duration prior only during coarse seed search, restores original fine fitting, and preserves the original freeze-before-holdout evaluation. Its saved training_seed_diagnostics describe the actual refinements; legacy config fields do not describe the new coarse duration family.",
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
    all_rows = references + rows
    methods = COMPARISONS + ["qualified_seeds"]
    counts = {
        m: dict(
            recovered=sum(r["recovered"] is True for r in all_rows if r["method"] == m),
            strict=sum(r["strict"] is True for r in all_rows if r["method"] == m),
            strict_and_all_screening_checks=sum(
                r["strict_and_all_screening_checks"] is True for r in all_rows if r["method"] == m
            ),
            unmodified_unflagged=sum(
                r["unflagged_fits"] for r in all_rows if r["method"] == m and r["null_diagnostic"]
            ),
        )
        for m in methods
    }
    paired = {
        m: {r["paired_id"]: r for r in all_rows if r["method"] == m and not r["null_diagnostic"]}
        for m in methods
    }
    lost = {
        m: [
            k
            for k, r in paired[m].items()
            if r["strict"] and not paired["qualified_seeds"][k]["strict"]
        ]
        for m in COMPARISONS
    }
    errors = [r for r in all_rows if r["status"] != "finished"]
    gate = bool(
        not errors
        and counts["qualified_seeds"]["strict"] >= max(counts[m]["strict"] for m in COMPARISONS) + 2
        and not any(lost.values())
        and counts["qualified_seeds"]["unmodified_unflagged"]
        <= counts["harmonic_three"]["unmodified_unflagged"]
    )
    report = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        new_runs=len(rows),
        reused_runs=len(references),
        rows=all_rows,
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
