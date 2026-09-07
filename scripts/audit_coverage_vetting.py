"""Audit provenance and nominal event arithmetic of the selected-fit review."""

from datetime import datetime, timezone
import json

from astropy.io import fits
import numpy as np

from coverage_pilot import ROOT, sha, save

OUT = ROOT / "reports/vetting/coverage_142086813"


def main():
    diagnostic = json.loads((OUT / "diagnostics.json").read_text())
    injection = json.loads((OUT / "sap_injection_diagnostic.json").read_text())
    checks, failures = 0, []

    def check(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    def score(events):
        if not events:
            return None
        d = np.array([e["depth"] for e in events])
        error = np.array([e["error"] for e in events])
        check(
            bool(np.all(np.isfinite(d)) and np.all(np.isfinite(error)) and np.all(error > 0)),
            "finite event inputs",
        )
        w = 1 / error**2
        return float(np.sum(w * d) / np.sqrt(w.sum()))

    def original(record):
        events = record["event_snr"]
        check(len(events) == record["n_observed_events"], "original event count")
        if events:
            check(
                bool(np.isclose(score(events), record["fixed_ephemeris_snr"], atol=1e-9)),
                "original event score",
            )

    def baseline(record):
        events = [e for e in record["event_measurements"] if e["status"] == "measured"]
        check(len(events) == record["events"], "baseline event count")
        if events:
            check(
                bool(np.isclose(score(events), record["nominal_snr"], atol=1e-9)),
                "baseline event score",
            )
            check(
                sum(e["depth"] > 0 for e in events) == record["positive_events"], "baseline signs"
            )

    for name, digest in diagnostic["source_sha256"].items():
        check(sha(ROOT / name) == digest, "diagnostic input " + name)
    for name, digest in {**injection["input_sha256"], **injection["source_sha256"]}.items():
        check(sha(ROOT / name) == digest, "injection input " + name)
    check(
        sha(OUT / "diagnostics.json") == injection["diagnostic_sha256"],
        "injection diagnostic reference",
    )
    check(
        sha(ROOT / "scripts/check_coverage_sap_injections.py") == injection["script_sha256"],
        "injection executable",
    )
    receipt = diagnostic["original_receipt"]
    folder = ROOT / "results/142086813_coverage_pilot"
    for name, digest in receipt["output_sha256"].items():
        check(sha(folder / name) == digest, "original receipt " + name)
    result = json.loads((folder / "result.json").read_text())
    check(result["signals"][1] == diagnostic["frozen_signal"], "unchanged supplied fit")
    check(sha(folder / "result.json") == injection["result_sha256"], "injection result reference")
    for parts in diagnostic["measurements"].values():
        for data in parts.values():
            original(data["original"])
            for b in data["baselines"]:
                baseline(b)
            for row in data["leave_one_out"]:
                kept = [
                    e for e in data["original"]["event_snr"] if e["cycle"] != row["removed_cycle"]
                ]
                check(
                    bool(np.isclose(score(kept), row["nominal_snr"], atol=1e-9)),
                    "leave-one-out score",
                )
    for part, saved_name in [("training", "discovery"), ("holdout", "holdout")]:
        replay = diagnostic["measurements"]["target_PDC_after"][part]["search_replay"]
        original(replay)
        check(
            bool(
                np.isclose(
                    replay["fixed_ephemeris_snr"],
                    result["signals"][1][saved_name]["fixed_ephemeris_snr"],
                    atol=1e-7,
                )
            ),
            "original masked training or full holdout replay",
        )
    crowding = {}
    for name in injection["input_sha256"]:
        with fits.open(ROOT / name, memmap=True) as h:
            check(int(h[0].header["TICID"]) == 142086813, "SAP input TIC")
            crowding[int(h[0].header["SECTOR"])] = float(h[1].header["CROWDSAP"])
    for row in injection["records"]:
        check(
            {m["sector"]: m["crowdsap"] for m in row["sector_crowding"]} == crowding,
            "exact header dilution per sector",
        )
        for stage, parts in row["parts"].items():
            for part, data in parts.items():
                original(data["original"])
                baseline(data["quadratic"])
                if row["shape"] == "zero":
                    reference = diagnostic["measurements"]["target_SAP_" + stage][part]["original"]
                    check(
                        bool(
                            np.isclose(
                                data["original"]["fixed_ephemeris_snr"],
                                reference["fixed_ephemeris_snr"],
                                atol=1e-7,
                            )
                        ),
                        "zero control reproduces SAP",
                    )
    record = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        checks=checks,
        failures=failures,
        passed=not failures,
        artifact_sha256={
            name: sha(OUT / name)
            for name in [
                "diagnostics.json",
                "summary.json",
                "sap_injection_diagnostic.json",
                "folds.png",
                "events.png",
            ]
        },
        auditor_sha256=sha(ROOT / "scripts/audit_coverage_vetting.py"),
        scope="Provenance, original second-fit mask replay, per-sector dilution and nominal arithmetic checks. Not independent astrophysical validation or a false-alarm probability.",
    )
    save(OUT / "audit.json", record)
    print(json.dumps({k: v for k, v in record.items() if k != "artifact_sha256"}, indent=2))
    if failures:
        raise ValueError("Vetting audit failed")


if __name__ == "__main__":
    main()
