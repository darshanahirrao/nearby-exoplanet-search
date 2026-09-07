"""Run the conditionally approved, fixed 100-star exploratory reanalysis."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import pandas as pd

from multimode_cycle_experiment import weak
from qualified_seeds import make_search
from search import known_matches, load_target

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/revised_pilot"
EPHEMERIS = ["period_days", "epoch_btjd", "duration_days", "depth"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def selected_method(confirmation, control, audit):
    method = confirmation.get("selected_for_exploratory_pilot")
    if (
        method not in ["coarse_only", "qualified_seeds"]
        or not confirmation.get("assessment_gate_passed")
        or not confirmation.get("gates", {}).get(method, {}).get("passed")
        or confirmation.get("errors")
        or not audit.get("passed")
    ):
        raise ValueError("Independent confirmation and its artifact audit must pass")
    retained = any(
        r["method"] == method
        and any(
            abs(m["toi"] - 700.02) < 1e-8 and m["strict"] and m["all_screening_checks"]
            for m in r["matches"]
        )
        for r in control["rows"]
    )
    if not retained:
        raise ValueError("The selected revision must retain real TOI-700 d")
    return method


def prepare():
    selection_path = ROOT / "provenance/revised_pilot_selection.json"
    confirmation_path = ROOT / "reports/experiments/pipeline_confirmation/results.json"
    control_path = ROOT / "reports/calibration/revised_pipeline/results.json"
    audit_path = ROOT / "reports/experiments/pipeline_confirmation/audit.json"
    selection = json.loads(selection_path.read_text())
    confirmation = json.loads(confirmation_path.read_text())
    control = json.loads(control_path.read_text())
    audit = json.loads(audit_path.read_text())
    method = selected_method(confirmation, control, audit)
    if (
        audit["results_sha256"] != sha(confirmation_path)
        or audit["plan_sha256"] != sha(ROOT / "reports/experiments/pipeline_confirmation/plan.json")
        or audit["auditor_sha256"] != sha(ROOT / "scripts/audit_confirmation.py")
    ):
        raise ValueError("Confirmation results changed after audit")
    files = {
        str(Path(__file__).relative_to(ROOT)),
        "docs/REVISED_PILOT_EXECUTION.md",
        "scripts/audit_confirmation.py",
    }
    files.update(
        str(p.relative_to(ROOT))
        for p in [selection_path, confirmation_path, control_path, audit_path]
    )
    for plan_path in [
        ROOT / "reports/experiments/pipeline_confirmation/plan.json",
        ROOT / "reports/calibration/revised_pipeline/plan.json",
        selection_path,
    ]:
        prior = json.loads(plan_path.read_text())
        files.add(str(plan_path.relative_to(ROOT)))
        for field in ["source_sha256", "input_sha256", "catalogue_sha256"]:
            for name, digest in prior.get(field, {}).items():
                if sha(ROOT / name) != digest:
                    raise ValueError(f"Frozen prerequisite changed: {name}")
                files.add(name)
    for row in control["rows"]:
        if sha(ROOT / row["result_path"]) != row["result_sha256"]:
            raise ValueError("Real control result changed")
        files.add(row["result_path"])
    targets = selection["targets"]
    if len(targets) != 100 or len({r["tic"] for r in targets}) != 100:
        raise ValueError("Expected exactly 100 unique frozen targets")
    count = 0
    for row in targets:
        expected = {r["path"] for r in row["telescope_inputs"]}
        actual = {
            str(p.relative_to(ROOT))
            for p in (ROOT / "data/lightcurves" / str(row["tic"])).glob("*_lc.fits")
        }
        if actual != expected:
            raise ValueError(f"Telescope input set changed: {row['tic']}")
        for record in row["telescope_inputs"]:
            path = ROOT / record["path"]
            if path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
                raise ValueError(f"Telescope input changed: {path}")
            count += 1
    spec = dict(
        source_sha256={name: sha(ROOT / name) for name in sorted(files)},
        method=method,
        selected_tics=[r["tic"] for r in targets],
        selection_sha256=sha(selection_path),
        telescope_files_checked=count,
        maximum_retained_fits=2,
        bls_threads_per_call=2,
        adapter_note=json.loads(
            (ROOT / "reports/experiments/pipeline_confirmation/plan.json").read_text()
        )["adapter_note"],
        claims="Exploratory reanalysis of already searched stars; no additional distinct stars or discoveries.",
    )
    REPORT.mkdir(parents=True, exist_ok=True)
    path = REPORT / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != v for k, v in spec.items()):
            raise ValueError("Preserve the frozen pilot execution")
    else:
        save(path, dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec))
    return spec, sha(path)


def checked_cache(tic, plan_hash):
    folder = ROOT / "results" / f"{tic}_revised_pilot"
    path = folder / "receipt.json"
    if not path.exists():
        return None
    receipt = json.loads(path.read_text())
    if receipt["tic"] != tic or receipt["plan_sha256"] != plan_hash:
        raise ValueError(f"Wrong cached pilot identity: {tic}")
    for name, digest in receipt["output_sha256"].items():
        if sha(folder / name) != digest:
            raise ValueError(f"Changed cached pilot output: {tic}/{name}")
    result = json.loads((folder / "result.json").read_text())
    frozen = json.loads((folder / "frozen_training.json").read_text())
    if len(result["signals"]) != len(frozen["signals"]) or any(
        any(a[k] != b[k] for k in EPHEMERIS) for a, b in zip(result["signals"], frozen["signals"])
    ):
        raise ValueError(f"Pilot ephemeris changed after holdout: {tic}")
    if set(result["training_sectors"]) & set(result["holdout_sectors"]):
        raise ValueError(f"Overlapping pilot sectors: {tic}")
    return receipt


def worker(tic, method, plan_hash):
    start = time.monotonic()
    folder = ROOT / "results" / f"{tic}_revised_pilot"
    # An incomplete prior attempt requires inspection; never silently overwrite it.
    folder.mkdir(exist_ok=False)
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[tic]
    original, metadata = load_target(tic)
    original.to_csv(
        folder / "unfiltered_lightcurve.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    processed, models = weak(original, star)
    processed.to_csv(
        folder / "lightcurve.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}
    )
    result = make_search(qualified=method == "qualified_seeds")(processed, star, folder)
    for signal in result["signals"]:
        signal["known_matches"] = known_matches(tic, signal["period_days"])
        if signal["known_matches"]:
            signal["screening_flags"].append("known_catalogue_signal_or_harmonic")
    result.update(
        tic=tic,
        star=star.to_dict(),
        method=method,
        plan_sha256=plan_hash,
        source_products=metadata,
        variability_models=models,
        processed_data_sha256=sha(folder / "lightcurve.csv.gz"),
        total_elapsed_seconds=time.monotonic() - start,
        claims="Exploratory reanalysis; an unflagged fit requires astrophysical review.",
    )
    save(folder / "result.json", result)
    receipt = dict(
        tic=tic,
        method=method,
        status=result["status"],
        plan_sha256=plan_hash,
        elapsed_seconds=result["total_elapsed_seconds"],
        fits=len(result["signals"]),
        unflagged=sum(not s["screening_flags"] for s in result["signals"]),
        result_path=str((folder / "result.json").relative_to(ROOT)),
        output_sha256={
            name: sha(folder / name)
            for name in [
                "result.json",
                "frozen_training.json",
                "lightcurve.csv.gz",
                "unfiltered_lightcurve.csv.gz",
            ]
        },
    )
    save(folder / "receipt.json", receipt)
    return checked_cache(tic, plan_hash)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run", action="store_true", help="Execute after checking and freezing inputs"
    )
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.workers < 1 or args.workers * 2 > (os.cpu_count() or 1):
        parser.error("Workers must fit two BLS threads each within the CPU count")
    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs/revised_pilot.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec, plan_hash = prepare()
        print(
            json.dumps(
                dict(
                    method=spec["method"],
                    selected=100,
                    checked_inputs=spec["telescope_files_checked"],
                    run=args.run,
                )
            ),
            flush=True,
        )
        if not args.run:
            return
        rows, pending = [], []
        for tic in spec["selected_tics"]:
            cached = checked_cache(tic, plan_hash)
            if cached:
                rows.append(cached)
            else:
                pending.append(tic)
        state = dict(
            started_utc=datetime.now(timezone.utc).isoformat(),
            plan_sha256=plan_hash,
            selected=100,
            method=spec["method"],
            workers=args.workers,
            rows=rows,
            errors=[],
        )

        def checkpoint():
            state["updated_utc"] = datetime.now(timezone.utc).isoformat()
            state["completed"] = len(rows)
            save(REPORT / "progress.json", state)

        checkpoint()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(worker, tic, spec["method"], plan_hash): tic for tic in pending}
            for future in as_completed(futures):
                tic = futures[future]
                try:
                    row = future.result()
                    rows.append(row)
                    print(
                        json.dumps(
                            {
                                k: row[k]
                                for k in ["tic", "status", "fits", "unflagged", "elapsed_seconds"]
                            }
                        ),
                        flush=True,
                    )
                except Exception as exc:
                    error = dict(tic=tic, error=repr(exc))
                    state["errors"].append(error)
                    print(json.dumps(error), flush=True)
                checkpoint()
        state.update(
            status="error" if state["errors"] else "finished",
            fits=sum(r["fits"] for r in rows),
            unflagged=sum(r["unflagged"] for r in rows),
            additional_distinct_stars=0,
        )
        save(REPORT / "results.json", state)
        print(json.dumps({k: v for k, v in state.items() if k != "rows"}), flush=True)
        if state["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
