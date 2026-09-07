"""Check the fixed comparison's case identities, hashes and recovery accounting."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / "reports/experiments/pipeline_confirmation"
    plan = json.loads((folder / "plan.json").read_text())
    result = json.loads((folder / "results.json").read_text())
    failures = []
    checks = 0

    def check(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    for field in ["source_sha256", "telescope_inputs_sha256", "catalogue_sha256"]:
        for name, digest in plan[field].items():
            check(sha(ROOT / name) == digest, name)
    check(
        sha(ROOT / "reports/experiments/realistic_duration/plan.json")
        == plan["template_plan_sha256"],
        "unchanged template plan",
    )
    check(
        sha(ROOT / "reports/experiments/qualified_seeds/results.json")
        == plan["prior_component_result_sha256"],
        "unchanged prior failed experiment",
    )
    expected = {c["id"]: c for c in plan["cases"]}
    rows = {r["id"]: r for r in result["rows"]}
    check(len(rows) == len(result["rows"]) == 240, "240 unique results")
    check(set(rows) == set(expected), "exact frozen case set")
    for key, row in rows.items():
        path = ROOT / row["result_path"]
        raw = json.loads(path.read_text())
        check(sha(path) == row["result_sha256"], key + " result hash")
        check(all(raw.get(k) == v for k, v in expected[key].items()), key + " case identity")
        check(raw["status"] == row["status"] == "finished", key + " finished")
        check(not set(raw["training_sectors"]) & set(raw["holdout_sectors"]), key + " sectors")
        frozen = json.loads((path.parent / "frozen_training.json").read_text())
        fitted = json.loads((path.parent / "frozen_search.json").read_text())["signals"]
        fields = ["period_days", "epoch_btjd", "duration_days", "depth"]
        check(
            len(frozen["signals"]) == len(fitted)
            and all(all(a[k] == b[k] for k in fields) for a, b in zip(frozen["signals"], fitted)),
            key + " frozen ephemerides",
        )
        check(
            row["unflagged_fits"] == sum(not s["screening_flags"] for s in fitted), key + " flags"
        )
        if not row["null_diagnostic"]:
            strict = any(
                m["nominal_snr"] >= 7
                and m["discovery_events"] >= 3
                and m["holdout"]["n_observed_events"] >= 2
                and (m["holdout"]["fixed_ephemeris_snr"] or 0) >= 5
                for m in raw["matches"]
            )
            all_checks = strict and any(
                not s["screening_flags"]
                and any(abs(s["period_days"] - m["period_days"]) < 1e-10 for m in raw["matches"])
                for s in fitted
            )
            check(row["recovered"] == bool(raw["matches"]), key + " recovery")
            check(row["strict"] == raw["recovered_with_strict_holdout"] == strict, key + " strict")
            check(row["strict_and_all_screening_checks"] == all_checks, key + " full checks")
    for method, saved in result["counts"].items():
        group = [r for r in rows.values() if r["method"] == method]
        check(len(group) == 60, method + " total")
        for key in ["recovered", "strict", "strict_and_all_screening_checks"]:
            check(saved[key] == sum(r[key] is True for r in group), method + " " + key)
        check(
            saved["unmodified_unflagged"]
            == sum(r["unflagged_fits"] for r in group if r["null_diagnostic"]),
            method + " unmodified fits",
        )
    report = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(folder / "plan.json"),
        results_sha256=sha(folder / "results.json"),
        auditor_sha256=sha(Path(__file__)),
        checks=checks,
        failures=failures,
        passed=not failures,
        scope="Artifact and recovery accounting audit; no astrophysical validity or false-alarm calibration.",
    )
    path = folder / "audit.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    if any(old.get(k) != v for k, v in report.items() if k != "checked_utc"):
        path.write_text(json.dumps(report, indent=2) + "\n")
    else:
        report = old
    print(json.dumps(report))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
