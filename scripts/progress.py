"""Compact live counts and review queue without dumping per-event measurements."""

from collections import Counter
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
        claims="Trial fits are not planet candidates or discoveries. Live snapshot; use final audits for publication.",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    print(json.dumps(snapshot(args.limit), indent=2))


if __name__ == "__main__":
    main()
