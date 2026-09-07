"""Audit the expanded-coverage inputs and export every retained trial fit."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from astropy.io import fits
import numpy as np

import coverage_pilot as pilot

ROOT, REPORT = pilot.ROOT, pilot.REPORT
PUBLIC_PLAN_COMMIT = "6f08d259dc6fd966559a7394f0500aa15730e99a"


def main():
    state = json.loads((REPORT / "results.json").read_text())
    plan = pilot.verify_plan()
    execution = json.loads((REPORT / "execution_plan.json").read_text())
    manifest = json.loads((REPORT / "download_manifest.json").read_text())
    execution_hash = pilot.sha(REPORT / "execution_plan.json")
    selected = {r["tic"] for r in plan["targets"]}
    if state["status"] != "finished" or state["errors"] or state["completed"] != len(selected):
        raise ValueError("Complete the entire pilot before final export")
    checks, failures = 0, []

    def check(condition, name):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(name)

    published_plan = subprocess.check_output(
        ["git", "show", PUBLIC_PLAN_COMMIT + ":reports/coverage_pilot/plan.json"], cwd=ROOT
    )
    check(
        published_plan == (REPORT / "plan.json").read_bytes(),
        "selection equals publicly frozen plan",
    )
    check(
        plan["frozen_utc"]
        <= manifest["started_utc"]
        <= manifest["completed_utc"]
        <= execution["frozen_utc"]
        <= state["started_utc"],
        "plan, download, execution freeze and search chronology",
    )
    check(
        execution["selection_plan_sha256"] == pilot.sha(REPORT / "plan.json"),
        "execution selection hash",
    )
    check(
        execution["download_manifest_sha256"] == pilot.sha(REPORT / "download_manifest.json"),
        "execution download hash",
    )
    check(state["execution_plan_sha256"] == execution_hash, "state execution hash")
    check(manifest["complete"] and not manifest["errors"], "complete download")
    check(len(manifest["files"]) == plan["additional_products"], "download count")
    receipts = {r["tic"]: r for r in state["rows"]}
    check(set(receipts) == selected and len(state["rows"]) == len(selected), "exact result set")
    cache = pilot.adapted_functions()["checked_cache"]
    trials, stars, products_checked = [], [], 0
    for target in plan["targets"]:
        tic = target["tic"]
        added = [r for r in manifest["files"] if r["tic"] == tic]
        check(
            {r["filename"] for r in added} == {r["filename"] for r in target["unused_products"]},
            f"{tic} selected extra products",
        )
        check(
            {p.name for p in (pilot.EXTRA / str(tic)).glob("*_lc.fits")}
            == {r["filename"] for r in added},
            f"{tic} extra directory contents",
        )
        check(
            {r["sector"] for r in added}.isdisjoint(target["old_sectors"]),
            f"{tic} old and extra sectors disjoint",
        )
        old_time, new_time = [], []
        for records, times in [(target["original_products"], old_time), (added, new_time)]:
            for record in records:
                path = ROOT / record["path"]
                check(
                    path.stat().st_size == record["bytes"] and pilot.sha(path) == record["sha256"],
                    f"input bytes {path.name}",
                )
                with fits.open(path, memmap=False) as h:
                    check(int(h[0].header["TICID"]) == tic, f"input TIC {path.name}")
                    check(
                        int(h[0].header["SECTOR"]) == record["sector"], f"input sector {path.name}"
                    )
                    time = np.asarray(h[1].data["TIME"], dtype=float)
                    time = time[np.isfinite(time)]
                    check(
                        len(time) > 0 and bool(np.all(np.diff(time) > 0)),
                        f"input times {path.name}",
                    )
                    times.append(time)
                products_checked += 1
        check(
            np.intersect1d(
                np.round(np.concatenate(old_time), 8), np.round(np.concatenate(new_time), 8)
            ).size
            == 0,
            f"{tic} no shared raw timestamps",
        )
        receipt = cache(tic, execution_hash)
        check(receipt == receipts[tic], f"{tic} exact checked receipt")
        result = json.loads((ROOT / receipt["result_path"]).read_text())
        frozen_path = ROOT / "results" / f"{tic}_coverage_pilot/frozen_training.json"
        frozen = json.loads(frozen_path.read_text())
        check(len(result["signals"]) <= plan["maximum_retained_fits"], f"{tic} trial budget")
        check(
            set(result["training_sectors"]).isdisjoint(result["holdout_sectors"]),
            f"{tic} training and holdout sectors disjoint",
        )
        expected_sectors = set(target["available_sectors"])
        actual_sectors = set(result["training_sectors"]) | set(result["holdout_sectors"])
        check(actual_sectors <= expected_sectors, f"{tic} processed sectors selected")
        for index, (signal, original) in enumerate(zip(result["signals"], frozen["signals"]), 1):
            for field in previous_ephemeris_fields():
                check(signal[field] == original[field], f"{tic} trial {index} frozen {field}")
            for part in ["discovery", "holdout"]:
                data = signal[part]
                events = data["event_snr"]
                if events:
                    depths = np.array([e["depth"] for e in events])
                    errors = np.array([e["error"] for e in events])
                    check(
                        bool(
                            np.all(np.isfinite(depths))
                            and np.all(np.isfinite(errors))
                            and np.all(errors > 0)
                        ),
                        f"{tic} trial {index} {part} finite events",
                    )
                    weights = 1 / errors**2
                    snr = float(np.sum(weights * depths) / np.sqrt(weights.sum()))
                    check(
                        bool(np.isclose(snr, data["fixed_ephemeris_snr"], atol=1e-9)),
                        f"{tic} trial {index} {part} event arithmetic",
                    )
                check(
                    len(events) == data["n_observed_events"],
                    f"{tic} trial {index} {part} event count",
                )
            trials.append(
                dict(
                    tic=tic,
                    signal_index=index,
                    result_path=receipt["result_path"],
                    result_sha256=receipt["output_sha256"]["result.json"],
                    frozen_training_sha256=receipt["output_sha256"]["frozen_training.json"],
                    training_sectors=result["training_sectors"],
                    holdout_sectors=result["holdout_sectors"],
                    star={k: result["star"][k] for k in ["Mass", "Rad", "Teff", "Tmag"]},
                    signal=signal,
                )
            )
        stars.append(
            dict(
                tic=tic,
                selected_sectors=len(expected_sectors),
                processed_sectors=len(actual_sectors),
                unused_after_quality_cuts=sorted(expected_sectors - actual_sectors),
                training_points=result["training_points"],
                holdout_points=result["holdout_points"],
            )
        )
    check(
        products_checked
        == execution["input_products"]
        == plan["original_products"] + plan["additional_products"],
        "all input products audited",
    )
    check(
        len(trials) == state["fits"] == sum(r["fits"] for r in receipts.values()),
        "trial accounting",
    )
    queue = [r for r in trials if not r["signal"]["screening_flags"]]
    check(
        len(queue) == state["unflagged"] == sum(r["unflagged"] for r in receipts.values()),
        "unflagged accounting",
    )
    audit = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        checks=checks,
        failures=failures,
        passed=not failures,
        products_checked=products_checked,
        completed_receipts=len(receipts),
        selection_plan_sha256=pilot.sha(REPORT / "plan.json"),
        execution_plan_sha256=execution_hash,
        results_sha256=pilot.sha(REPORT / "results.json"),
        exporter_sha256=pilot.sha(Path(__file__)),
        scope="Input, timing separation, frozen-parameter and arithmetic audit. Does not establish astrophysical validity or calibrated significance.",
    )
    pilot.save(REPORT / "audit.json", audit)
    if failures:
        raise ValueError("Audit failures: " + "; ".join(failures))
    summary = dict(
        exported_utc=datetime.now(timezone.utc).isoformat(),
        reanalysed_stars=len(selected),
        additional_distinct_stars=0,
        selected_sector_products=products_checked,
        usable_sectors=sum(s["processed_sectors"] for s in stars),
        trial_fits=len(trials),
        unflagged=len(queue),
        flags=dict(
            sorted(Counter(f for r in trials for f in r["signal"]["screening_flags"]).items())
        ),
        stars=stars,
        queue=[
            {k: r[k] for k in ["tic", "signal_index", "result_path", "result_sha256"]}
            for r in queue
        ],
        scope="All retained fits disclosed. Flags overlap. Exploratory old-plus-new data reanalysis, not an independent completeness study. Every unflagged fit needs astrophysical vetting.",
    )
    for name, value in [("trials.json", trials), ("summary.json", summary)]:
        (REPORT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "stars"}, indent=2))
    print("Audit checks", checks, "failures", len(failures))


def previous_ephemeris_fields():
    return ["period_days", "epoch_btjd", "duration_days", "depth"]


if __name__ == "__main__":
    main()
