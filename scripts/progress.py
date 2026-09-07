"""Compact live counts and review queue without dumping per-event measurements."""

from collections import Counter
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pilot_snapshot():
    folder = ROOT / "reports/revised_pilot"
    result = folder / "results.json"
    progress = folder / "progress.json"
    path = result if result.exists() else progress
    if not path.exists():
        return dict(state="prepared_without_run_outputs")
    data = json.loads(path.read_text())
    return dict(
        state=data.get("status", "partial_outputs"),
        method=data["method"],
        selected=data["selected"],
        completed=data["completed"],
        trial_fits=sum(r["fits"] for r in data["rows"]),
        unflagged=sum(r["unflagged"] for r in data["rows"]),
        errors=len(data["errors"]),
        additional_distinct_stars=0,
    )


def experiment_snapshot():
    rows = []
    for path in sorted((ROOT / "reports/experiments").glob("*/plan.json")):
        try:
            plan = json.loads(path.read_text())
            if not isinstance(plan.get("cases"), list):
                continue
            result_path = path.with_name("results.json")
            progress_path = path.with_name("progress.json")
            row = dict(
                experiment=path.parent.name,
                planned_new_runs=len(plan["cases"]),
                frozen_utc=plan.get("frozen_utc"),
            )
            if result_path.exists():
                result = json.loads(result_path.read_text())
                row.update(
                    state="completed",
                    completed_new_runs=result.get("new_runs", len(result.get("rows", []))),
                    reused_runs=result.get("reused_runs", 0),
                    gate_passed=result.get(
                        "development_gate_passed", result.get("assessment_gate_passed")
                    ),
                    errors=len(result.get("errors", [])),
                    counts=result.get("counts"),
                )
            elif progress_path.exists():
                progress = json.loads(progress_path.read_text())
                row.update(
                    state="partial_outputs",
                    completed_new_runs=progress.get("completed"),
                    errors=sum(r.get("status") != "finished" for r in progress.get("rows", [])),
                )
            else:
                row.update(state="prepared_without_run_outputs", completed_new_runs=0)
            rows.append(row)
        except (OSError, json.JSONDecodeError):
            rows.append(dict(experiment=path.parent.name, state="snapshot_unreadable_retry"))
    return dict(
        experiments=rows,
        revised_pilot=pilot_snapshot(),
        note="Output state only; partial files do not prove a process is still running. Synthetic recoveries are not discoveries.",
    )


def snapshot(limit=12):
    ledger = ROOT / "reports/vetting/unflagged_review.json"
    reviewed = (
        {(r["result_path"], r["signal_index"]) for r in json.loads(ledger.read_text())["trials"]}
        if ledger.exists()
        else set()
    )
    counts = {
        name: Counter()
        for name in ["base", "refined", "variability", "longbaseline", "known_residual"]
    }
    searched = set()
    unreviewed, unreadable = [], []
    base, combined = set(), set()
    for path in (ROOT / "results").glob("*/result.json"):
        parts = path.parent.name.split("_", 1)
        if not parts[0].isdigit():
            continue
        variant = parts[1] if len(parts) == 2 else "base"
        if variant not in counts:
            continue
        if parts[0] == "150428135" and variant != "known_residual":
            continue
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            unreadable.append(str(path.relative_to(ROOT)))
            continue
        tic = int(parts[0])
        stats = counts[variant]
        stats["results"] += 1
        signals = result.get("signals", [])
        stats["trial_fits"] += len(signals)
        stats["skipped"] += str(result.get("status", "")).startswith("skipped")
        stats["unflagged"] += sum(s.get("screening_flags") == [] for s in signals)
        if signals:
            searched.add(tic)
        if variant == "base":
            base.add(tic)
        elif variant == "longbaseline":
            combined.add(tic)
        for index, signal in enumerate(signals, 1):
            if (
                signal.get("screening_flags") == []
                and (str(path.relative_to(ROOT)), index) not in reviewed
            ):
                unreviewed.append(
                    dict(
                        tic=tic,
                        variant=variant,
                        signal_index=index,
                        period_days=signal["period_days"],
                        result=str(path.relative_to(ROOT)),
                    )
                )
    state = ROOT / "logs/final_stages.json"
    stage = json.loads(state.read_text()) if state.exists() else {}
    return dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        stage=stage.get("stage"),
        counts=counts,
        distinct_stars_with_trial_fits=len(searched),
        pending_combined=len(base - combined),
        unreviewed_unflagged_count=len(unreviewed),
        unreviewed_unflagged=sorted(
            unreviewed, key=lambda r: (r["tic"], r["variant"], r["signal_index"])
        )[:limit],
        unreadable_files=unreadable[:limit],
        revised_pilot=pilot_snapshot(),
        claims="Trial fits are not planet candidates or discoveries. Live snapshot; use final audits for publication.",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--experiments-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    print(
        json.dumps(
            experiment_snapshot() if args.experiments_only else snapshot(args.limit), indent=2
        )
    )


if __name__ == "__main__":
    main()
