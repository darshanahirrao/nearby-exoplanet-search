"""A separately frozen new-star comparison of two complete pipeline revisions."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import injections
import longbaseline
import physical_duration_experiment as physical
import qualified_seed_experiment as qualified
from qualified_seeds import ORIGINAL_SEARCH
from realistic_injections import make_loader

ROOT = Path(__file__).resolve().parents[1]
SUITE = "pipeline_confirmation"
METHODS = ["production", "harmonic_three", "coarse_only", "qualified_seeds"]


def worker(case):
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[case["tic"]]
    injections.load_target = make_loader(case, star)
    if case["method"] in METHODS[:2]:
        longbaseline.search_combined = ORIGINAL_SEARCH
        physical.SUITE = SUITE
        return physical.worker(case)
    qualified.SUITE = SUITE
    return qualified.worker(case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    out = ROOT / "reports/experiments/pipeline_confirmation"
    out.mkdir(parents=True, exist_ok=True)
    template_path = ROOT / "reports/experiments/realistic_duration/plan.json"
    prior_path = ROOT / "reports/experiments/qualified_seeds/plan.json"
    prior_result = ROOT / "reports/experiments/qualified_seeds/results.json"
    template = json.loads(template_path.read_text())
    prior = json.loads(prior_path.read_text())
    files = sorted(
        set(template["source_sha256"])
        | set(prior["source_sha256"])
        | {"docs/EXPERIMENT_PIPELINE_CONFIRMATION.md", "scripts/pipeline_confirmation.py"}
    )
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    for original in [template, prior]:
        if any(hashes[p] != digest for p, digest in original["source_sha256"].items()):
            raise ValueError("A frozen method or injection adapter changed")
    path = out / "plan.json"
    if path.exists():
        plan = json.loads(path.read_text())
        if (
            plan["source_sha256"] != hashes
            or plan["template_plan_sha256"]
            != hashlib.sha256(template_path.read_bytes()).hexdigest()
        ):
            raise ValueError("Preserve the frozen confirmation protocol and cases")
    else:
        base = [c for c in template["cases"] if c["method"] == "production"]
        cases = [
            dict(c, id=m + "__" + c["paired_id"], method=m, suite=SUITE)
            for c in base
            for m in METHODS
        ]
        if len(cases) != 240:
            raise ValueError("Expected 240 new method runs")
        plan = dict(
            frozen_utc=datetime.now(timezone.utc).isoformat(),
            source_sha256=hashes,
            template_plan_sha256=hashlib.sha256(template_path.read_bytes()).hexdigest(),
            prior_component_result_sha256=hashlib.sha256(prior_result.read_bytes()).hexdigest(),
            prior_component_gate_passed=json.loads(prior_result.read_text())[
                "development_gate_passed"
            ],
            selected_tics=template["selected_tics"],
            cases=cases,
            telescope_inputs_sha256=template["telescope_inputs_sha256"],
            catalogue_sha256=template["catalogue_sha256"],
            packages=template["packages"],
            scope="New-star comparison of complete fixed revisions; prior component gate remains failed. No planet, novelty or general completeness established.",
            adapter_note=prior["adapter_note"],
        )
        path.write_text(json.dumps(plan, indent=2) + "\n")
    for name, digest in {**plan["telescope_inputs_sha256"], **plan["catalogue_sha256"]}.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Frozen input changed: {name}")
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
            median_elapsed_seconds=float(
                np.median([r["elapsed_seconds"] for r in rows if r["method"] == m])
            ),
        )
        for m in METHODS
    }
    paired = {
        m: {r["paired_id"]: r for r in rows if r["method"] == m and not r["null_diagnostic"]}
        for m in METHODS
    }
    stronger = max(METHODS[:2], key=lambda m: counts[m]["strict"])
    errors = [r for r in rows if r["status"] != "finished"]
    gates = {}
    for method in METHODS[2:]:
        lost = {
            m: [k for k, r in paired[m].items() if r["strict"] and not paired[method][k]["strict"]]
            for m in METHODS[:2]
        }
        gained = [
            k
            for k, r in paired[method].items()
            if r["strict"] and not paired[stronger][k]["strict"]
        ]
        stars_gained = sorted({paired[method][k]["tic"] for k in gained})
        passed = bool(
            not errors
            and counts[method]["strict"] >= counts[stronger]["strict"] + 2
            and not any(lost.values())
            and counts[method]["strict_and_all_screening_checks"]
            >= max(counts[m]["strict_and_all_screening_checks"] for m in METHODS[:2])
            and counts[method]["unmodified_unflagged"]
            <= counts["harmonic_three"]["unmodified_unflagged"]
            and len(stars_gained) >= 2
        )
        gates[method] = dict(
            passed=passed,
            lost_legacy_strict=lost,
            gains_over_stronger_legacy=gained,
            stars_with_gains=stars_gained,
        )
    passing = [m for m in METHODS[2:] if gates[m]["passed"]]
    selected = (
        max(
            passing,
            key=lambda m: (
                counts[m]["strict_and_all_screening_checks"],
                counts[m]["strict"],
                -counts[m]["median_elapsed_seconds"],
            ),
        )
        if passing
        else None
    )
    report = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        rows=rows,
        counts=counts,
        errors=errors,
        gates=gates,
        assessment_gate_passed=bool(passing),
        selected_for_exploratory_pilot=selected,
    )
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
