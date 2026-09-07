"""Audit the completed capacity experiment and export its unmodified-star review queue."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / "reports/experiments/portfolio"
    plan = json.loads((folder / "plan.json").read_text())
    report = json.loads((folder / "results.json").read_text())
    expected = {c["id"]: c for c in plan["cases"]}
    references = {r["id"]: r for r in plan["reused_reference_rows"]}
    rows = {r["id"]: r for r in report["rows"]}
    failures, queue = [], []
    checks = 0

    def check(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    for name, digest in plan["source_sha256"].items():
        check(sha(ROOT / name) == digest, name)
    check(len(rows) == len(report["rows"]) == 180, "unique 180 result rows")
    check(set(rows) == set(expected) | set(references), "exact new and reused case sets")
    for key, row in rows.items():
        path = ROOT / row["result_path"]
        raw = json.loads(path.read_text())
        check(sha(path) == row["result_sha256"], key + " result hash")
        check(row["status"] == raw["status"] == "finished", key + " completion")
        if key in expected:
            check(all(raw.get(k) == v for k, v in expected[key].items()), key + " exact case")
        else:
            check(row == references[key], key + " exact reused reference")
        frozen_path = path.parent / "frozen_training.json"
        frozen = json.loads(frozen_path.read_text())
        final = json.loads((path.parent / "frozen_search.json").read_text())
        limit = 2 if row["method"] == "coarse_only" else 32
        check(
            raw["maximum_trial_fits"] == final["config"]["maximum_trial_fits"] == limit,
            key + " actual fit limit",
        )
        check(len(final["signals"]) == len(frozen["signals"]) <= limit, key + " fit count")
        check(
            not set(frozen["training_sectors"]) & set(frozen["holdout_sectors"]),
            key + " disjoint sectors",
        )
        for index, (a, b) in enumerate(zip(frozen["signals"], final["signals"]), 1):
            check(
                all(a[k] == b[k] for k in ["period_days", "epoch_btjd", "duration_days", "depth"]),
                key + f" frozen fit {index}",
            )
            if row["null_diagnostic"] and not b["screening_flags"]:
                queue.append(
                    dict(
                        tic=row["tic"],
                        method=row["method"],
                        signal_index=index,
                        result_path=row["result_path"],
                        result_sha256=row["result_sha256"],
                        frozen_training_sha256=sha(frozen_path),
                        signal=b,
                        disposition="Unverified trial fit requiring astrophysical review; no candidate or planet promoted.",
                    )
                )
        check(
            row["unflagged_fits"] == sum(not s["screening_flags"] for s in final["signals"]),
            key + " flag accounting",
        )
        if not row["null_diagnostic"]:
            strict = any(
                m["nominal_snr"] >= 7
                and m["discovery_events"] >= 3
                and m["holdout"]["n_observed_events"] >= 2
                and (m["holdout"]["fixed_ephemeris_snr"] or 0) >= 5
                for m in raw["matches"]
            )
            check(
                row["strict"] == raw["recovered_with_strict_holdout"] == strict,
                key + " strict accounting",
            )
            check(row["recovered"] == bool(raw["matches"]), key + " recovery accounting")
            full = strict and any(
                not s["screening_flags"]
                and any(abs(s["period_days"] - m["period_days"]) < 1e-10 for m in raw["matches"])
                for s in final["signals"]
            )
            check(row["strict_and_all_screening_checks"] == full, key + " all-check accounting")
    for method, counts in report["counts"].items():
        group = [r for r in rows.values() if r["method"] == method]
        for field in ["recovered", "strict", "strict_and_all_screening_checks"]:
            check(counts[field] == sum(r[field] is True for r in group), method + " " + field)
        check(
            counts["unmodified_unflagged"]
            == sum(r["unflagged_fits"] for r in group if r["null_diagnostic"]),
            method + " unmodified accounting",
        )
    result = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(folder / "plan.json"),
        results_sha256=sha(folder / "results.json"),
        auditor_sha256=sha(Path(__file__)),
        checks=checks,
        failures=failures,
        passed=not failures,
        unmodified_unflagged_fits=len(queue),
        scope="Artifact and accounting audit; not astrophysical validity, completeness or false-alarm calibration.",
    )
    (folder / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (folder / "unmodified_review_queue.json").write_text(
        json.dumps(
            dict(
                trials=queue,
                scope="Fits from explicitly uninjected controls, not synthetic planets and not validated candidates.",
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(result))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
