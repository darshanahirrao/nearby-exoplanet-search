"""Audit saved ephemerides and available provenance; does not validate planets."""

from collections import Counter
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("period_days", "epoch_btjd", "duration_days", "depth")
PATTERN = re.compile(
    r"\d+(?:_calibration_v2)?(?:_refined|_variability|_longbaseline|_known_residual|_targeted_multimode)?"
)


def coverage():
    selection = ROOT / "provenance/main_target_selection.csv"
    if not selection.exists():
        return dict(available=False, pending=[])
    with selection.open() as stream:
        tics = [int(row["tic"]) for row in csv.DictReader(stream)]
    pending, insufficient, usable = [], [], []
    for tic in tics:
        path = ROOT / "data/download_status" / f"{tic}.json"
        if not path.exists():
            pending.append(dict(tic=tic, stage="download_status"))
            continue
        downloaded = json.loads(path.read_text())
        if downloaded["state"] == "downloading":
            pending.append(dict(tic=tic, stage="download"))
        elif len(downloaded.get("files", [])) < 2:
            insufficient.append(dict(tic=tic, download_state=downloaded["state"]))
        else:
            usable.append(tic)
            for suffix in ["", "_refined", "_variability", "_longbaseline"]:
                result = ROOT / "results" / f"{tic}{suffix}" / "result.json"
                if not result.exists():
                    pending.append(dict(tic=tic, stage=suffix.lstrip("_") or "base"))
    plan = ROOT / "provenance/known_host_search_plan.json"
    known = json.loads(plan.read_text())["targets"] if plan.exists() else []
    for tic in known:
        if not (ROOT / "results" / f"{tic}_known_residual" / "result.json").exists():
            pending.append(dict(tic=tic, stage="known_residual"))
    return dict(
        available=True,
        main_selected=len(tics),
        main_usable_downloads=len(usable),
        insufficient_downloads=insufficient,
        known_hosts_selected=len(known),
        selected_overlap=len(set(tics) & set(known)),
        distinct_selected=len(set(tics) | set(known)),
        pending=pending,
    )


def audit(require_complete=False):
    counts = Counter()
    failures = []
    rows = []
    unreviewed = []
    ledger_path = ROOT / "reports/vetting/unflagged_review.json"
    ledger = json.loads(ledger_path.read_text())["trials"] if ledger_path.exists() else []
    reviews = {(r["result_path"], r["signal_index"]): r for r in ledger}

    def check(condition, name, path):
        counts[name] += 1
        if not condition:
            failures.append(dict(check=name, result=str(path.relative_to(ROOT))))

    for path in sorted((ROOT / "results").glob("*/result.json")):
        name = path.parent.name
        if not PATTERN.fullmatch(name) or name == "150428135":
            continue
        result = json.loads(path.read_text())
        signals = result.get("signals", [])
        row = dict(result=str(path.relative_to(ROOT)), trials=len(signals))
        rows.append(row)
        if not signals:
            continue
        if name.endswith(("_longbaseline", "_known_residual", "_targeted_multimode")):
            frozen_path = path.parent / "frozen_training.json"
            check(
                not (set(result["training_sectors"]) & set(result["holdout_sectors"])),
                "combined_training_holdout_sectors_disjoint",
                path,
            )
        elif name.endswith(("_refined", "_variability")):
            frozen_path = path.parent / "frozen_refinement.json"
            if result.get("reuse_reason"):
                frozen_path = (
                    path.parent.with_name(name.replace("_variability", "_refined"))
                    / "frozen_refinement.json"
                )
        else:
            frozen_path = path.parent / "frozen_discovery.json"
        check(frozen_path.exists(), "frozen_record_present", path)
        if frozen_path.exists():
            frozen = json.loads(frozen_path.read_text())
            row["frozen_record"] = str(frozen_path.relative_to(ROOT))
            row["frozen_sha256"] = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
            check(len(signals) == len(frozen["signals"]), "trial_count_unchanged", path)
            for old, final in zip(frozen["signals"], signals):
                check(
                    all(key in old and key in final and old[key] == final[key] for key in FIELDS),
                    "ephemeris_and_depth_unchanged_after_freeze",
                    path,
                )
                check(
                    "holdout" not in old and "validation" not in old,
                    "frozen_trial_has_no_holdout_measurement",
                    path,
                )
        for index, signal in enumerate(signals, 1):
            check(
                not signal.get("known_matches")
                or bool(
                    {
                        "known_catalogue_signal_or_harmonic",
                        "known_period_or_harmonic_requires_ephemeris_review",
                    }
                    & set(signal["screening_flags"])
                ),
                "catalogue_match_is_flagged",
                path,
            )
            if signal.get("screening_flags") == []:
                key = (str(path.relative_to(ROOT)), index)
                if key not in reviews:
                    unreviewed.append(dict(result=key[0], signal_index=index))
                else:
                    reviewed = reviews[key]
                    check(
                        reviewed["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
                        and reviewed["period_days"] == signal["period_days"]
                        and (ROOT / "reports/vetting" / reviewed["evidence"]).is_file(),
                        "review_ledger_matches_saved_trial",
                        path,
                    )
        hash_targets = []
        if "source_result" in result and "source_result_sha256" in result:
            hash_targets.append((ROOT / result["source_result"], result["source_result_sha256"]))
        if "source_data" in result and "source_sha256" in result:
            hash_targets.append((ROOT / result["source_data"], result["source_sha256"]))
        if "processed_data_sha256" in result:
            hash_targets.append(
                (path.parent / "lightcurve.csv.gz", result["processed_data_sha256"])
            )
        for source, expected in hash_targets:
            check(
                source.exists() and hashlib.sha256(source.read_bytes()).hexdigest() == expected,
                "available_source_or_processed_hash_matches",
                path,
            )
    report = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        result_files=len(rows),
        checks=dict(counts),
        failures=failures,
        execution_coverage=coverage(),
        unreviewed_unflagged_trials=unreviewed,
        scope="Main searches, corrected known-planet calibration and targeted multimode diagnostic. The obsolete initial TOI-700 calibration and synthetic injection suites are excluded.",
        limitations="Audits consistency of saved artifacts. It cannot prove that data were never inspected, establish a calibrated false-alarm rate, or validate an astrophysical interpretation. Refinement can split one sector in time, so only combined-season searches require disjoint sector identifiers here.",
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (ROOT / "reports/result_audit.json").write_text(json.dumps(report, indent=2))
    (ROOT / "provenance/frozen_records.json").write_text(json.dumps(rows, indent=2))
    print(json.dumps(report, indent=2))
    if failures or (
        require_complete
        and (
            not report["execution_coverage"]["available"]
            or report["execution_coverage"]["pending"]
            or unreviewed
        )
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    audit(parser.parse_args().require_complete)
