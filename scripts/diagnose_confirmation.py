"""Retrospective known-truth diagnostic of the completed physical injections.

This forces the injected period, epoch and total duration. It is not blind
recovery, a new experiment gate, or an estimate of search completeness. The
event-depth SNR differs from the BLS training statistic used for selection.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from longbaseline import sector_split
from multimode_cycle_experiment import weak
from realistic_injections import make_loader
from search import event_checks

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(frame, case):
    result = event_checks(frame, case["period_days"], case["epoch_btjd"], case["duration_days"])
    return {k: v for k, v in result.items() if k != "event_snr"}


def main():
    folder = ROOT / "reports/experiments/confirmation_diagnostic"
    folder.mkdir(exist_ok=True)
    source = ROOT / "reports/experiments/pipeline_confirmation"
    plan = json.loads((source / "plan.json").read_text())
    results = json.loads((source / "results.json").read_text())
    references = {r["id"]: r for r in results["rows"]}
    files = {**plan["source_sha256"], **plan["catalogue_sha256"], **plan["telescope_inputs_sha256"]}
    for name, digest in files.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Confirmation input changed: {name}")
    files.update(
        {
            str(p.relative_to(ROOT)): sha(p)
            for p in [Path(__file__), source / "plan.json", source / "results.json"]
        }
    )
    cases = [c for c in plan["cases"] if c["method"] == "coarse_only" and not c["null_diagnostic"]]
    spec = dict(source_sha256=files, case_ids=[c["id"] for c in cases], interpretation=__doc__)
    manifest = folder / "plan.json"
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        if any(previous[k] != v for k, v in spec.items()):
            raise ValueError("Diagnostic inputs changed")
    else:
        manifest.write_text(
            json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec), indent=2)
            + "\n"
        )
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    rows = []
    for case in cases:
        path = folder / (case["paired_id"] + ".json")
        if path.exists():
            row = json.loads(path.read_text())
        else:
            star = stars.loc[case["tic"]]
            original, _ = make_loader(case, star)(
                case["tic"],
                inject=dict(
                    period=case["period_days"],
                    epoch=case["epoch_btjd"],
                    depth=case["depth"],
                    duration=case["duration_days"],
                ),
            )
            filtered, _ = weak(original, star)
            row = dict(
                id=case["id"],
                tic=case["tic"],
                radius_earth=case["radius_earth"],
                duration_minutes=case["duration_days"] * 1440,
                blind_recovered=references[case["id"]]["recovered"],
                blind_strict=references[case["id"]]["strict"],
            )
            for name, data in [("before_harmonics", original), ("after_harmonics", filtered)]:
                training, holdout = sector_split(data)
                row[name] = dict(training=compact(training, case), holdout=compact(holdout, case))
            path.write_text(json.dumps(row, indent=2) + "\n")
        rows.append(row)
        (folder / "progress.json").write_text(
            json.dumps(dict(completed=len(rows), total=len(cases))) + "\n"
        )
        print(json.dumps(dict(completed=len(rows), id=row["id"])), flush=True)
    summary = {}
    for stage in ["before_harmonics", "after_harmonics"]:
        observable = [
            r
            for r in rows
            if r[stage]["training"]["n_observed_events"] >= 3
            and r[stage]["holdout"]["n_observed_events"] >= 2
        ]
        positive = [
            r
            for r in observable
            if (r[stage]["training"]["fixed_ephemeris_snr"] or 0) >= 7
            and (r[stage]["holdout"]["fixed_ephemeris_snr"] or 0) >= 5
        ]
        summary[stage] = dict(
            enough_sampled_events=len(observable),
            known_truth_event_snr_at_least_7_and_5=len(positive),
            above_reference_snr_but_not_blind_strict=[
                r["id"] for r in positive if not r["blind_strict"]
            ],
        )
    report = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        rows=rows,
        summary=summary,
        interpretation=__doc__,
    )
    (folder / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
