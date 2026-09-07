"""Audit fixed follow-up provenance and arithmetic; not astrophysical validation."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np
from astropy.io import fits

import followup_portfolio_trials as followup

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PLAN_COMMIT = "98a83917fa4f25cbb6cf4f5ad448b480952d35f9"


def main():
    out = followup.OUT
    plan = followup.verify_plan()
    manifest = json.loads((out / "download_manifest.json").read_text())
    results = json.loads((out / "results.json").read_text())
    checks, failures = 0, []

    def check(condition, name):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(name)

    def close(actual, expected, name):
        check(bool(np.isclose(actual, expected, atol=1e-9, rtol=1e-10)), name)

    frozen = subprocess.check_output(
        ["git", "show", PUBLIC_PLAN_COMMIT + ":reports/vetting/fresh_sector_followup/plan.json"],
        cwd=ROOT,
    )
    check(frozen == (out / "plan.json").read_bytes(), "plan matches published commit")
    check(
        plan["frozen_utc"] < manifest["completed_utc"] < results["completed_utc"],
        "preparation precedes completed download and analysis",
    )
    check(not manifest["errors"], "no download errors")
    selected = {p["sector"] for p in plan["selected_products"]}
    check(len(selected) == 21, "all 21 selected sectors")
    check({r["sector"] for r in manifest["files"]} == selected, "manifest complete")
    check(len(manifest["files"]) == len(selected), "no duplicate sector products")
    check(selected.isdisjoint(plan["original_sectors"]), "original and fresh sectors disjoint")
    for name, digest in plan["previous_input_sha256"].items():
        check(followup.sha(ROOT / name) == digest, "original hash " + name)
    for name, digest in plan["source_sha256"].items():
        check(followup.sha(ROOT / "scripts" / name) == digest, "frozen helper " + name)
    original_times, fresh_times = [], []
    old_sources = sorted((ROOT / "data/lightcurves/233738219").glob("*_lc.fits"))
    check(
        {str(p.relative_to(ROOT)) for p in old_sources}
        == {p for p in plan["previous_input_sha256"] if p.endswith("_lc.fits")},
        "original directory contains exactly frozen light curves",
    )
    for path in old_sources:
        with fits.open(path, memmap=False) as h:
            t = np.asarray(h[1].data["TIME"], dtype=float)
            original_times.extend(t[np.isfinite(t)].tolist())
    for record in manifest["files"]:
        path = ROOT / record["path"]
        check(followup.sha(path) == record["sha256"], "fresh hash " + path.name)
        with fits.open(path, memmap=False) as h:
            check(int(h[0].header["TICID"]) == plan["tic"], "fresh TIC identity " + path.name)
            check(
                int(h[0].header["SECTOR"]) == record["sector"], "fresh sector identity " + path.name
            )
            t = np.asarray(h[1].data["TIME"], dtype=float)
            fresh_times.extend(t[np.isfinite(t)].tolist())
    check(
        np.intersect1d(np.round(original_times, 8), np.round(fresh_times, 8)).size == 0,
        "no shared raw timestamps",
    )
    check(results["plan_sha256"] == followup.sha(out / "plan.json"), "result plan hash")
    check(
        results["manifest_sha256"] == followup.sha(out / "download_manifest.json"),
        "result manifest hash",
    )
    summaries = {r["method"]: r for r in results["rows"]}
    check(set(summaries) == {s["method"] for s in plan["signals"]}, "exactly both planned trials")
    for signal in plan["signals"]:
        method = signal["method"]
        row = json.loads((out / (method + ".json")).read_text())
        check(
            followup.sha(ROOT / signal["source"]) == signal["source_sha256"],
            "original trial source " + method,
        )
        for name in ["period_days", "epoch_btjd", "duration_days"]:
            check(row[name] == signal[name] == summaries[method][name], method + " frozen " + name)
        for flux, stages in row["views"].items():
            for stage, value in stages.items():
                label = method + " " + flux + " " + stage
                check(set(value["sectors"]) == selected, label + " all sectors processed")
                for kind in ["original", "quadratic"]:
                    result = value[kind]
                    events = (
                        result["event_snr"]
                        if kind == "original"
                        else [e for e in result["event_measurements"] if e["status"] == "measured"]
                    )
                    depth = np.array([e["depth"] for e in events])
                    error = np.array([e["error"] for e in events])
                    check(
                        bool(np.all(np.isfinite(depth)) and np.all(error > 0)),
                        label + kind + " finite events",
                    )
                    weight = 1 / error**2
                    snr = float(np.sum(weight * depth) / np.sqrt(weight.sum()))
                    actual = (
                        result["fixed_ephemeris_snr"]
                        if kind == "original"
                        else result["nominal_snr"]
                    )
                    close(actual, snr, label + kind + " event arithmetic")
                    close(
                        summaries[method]["scores"][flux][stage][kind],
                        snr,
                        label + kind + " summary score",
                    )
                    expected_count = (
                        result["n_observed_events"] if kind == "original" else result["events"]
                    )
                    check(len(events) == expected_count, label + kind + " event count")
                    if flux == "PDCSAP_FLUX" and stage == "after_harmonics":
                        fraction = float(np.mean(depth > 0))
                        passed = (
                            len(events) >= plan["checks"]["minimum_measurable_events"]
                            and fraction >= plan["checks"]["minimum_positive_fraction"]
                            and snr >= plan["checks"]["minimum_nominal_pdc_snr"]
                        )
                        c = row["recurrence_screen"]["checks"][kind]
                        check(c["passed"] == passed, label + kind + " recurrence criterion")
                        close(c["positive_fraction"], fraction, label + kind + " positive fraction")
                classes = value["rotation_phase_classes"]
                check(
                    [c["phase_class"] for c in classes] == list(range(value["phase_divisor"])),
                    label + " all phase classes saved",
                )
                close(
                    classes[0]["total_snr"],
                    value["original"]["fixed_ephemeris_snr"],
                    label + " unshifted phase agrees",
                )
        check(
            row["recurrence_screen"] == summaries[method]["recurrence_screen"],
            method + " summary recurrence agrees",
        )
        check(
            row["recurrence_screen"]["passed"]
            == all(c["passed"] for c in row["recurrence_screen"]["checks"].values()),
            method + " combined screen",
        )
    audit = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        checks=checks,
        failures=failures,
        passed=not failures,
        published_plan_commit=PUBLIC_PLAN_COMMIT,
        plan_sha256=followup.sha(out / "plan.json"),
        results_sha256=followup.sha(out / "results.json"),
        auditor_sha256=followup.sha(Path(__file__)),
        scope="Provenance and arithmetic audit, including raw time separation. Not proof of an astrophysical interpretation or calibrated significance.",
    )
    followup.write(out / "audit.json", audit)
    print(json.dumps(audit, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
