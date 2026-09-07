"""A frozen 20-star, full-coverage pilot with the previously qualified revision.

Reuse the original search worker and receipt checker, changing only their output
directory and light-curve loader. Original input directories remain unchanged.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import inspect
import json
import os
from pathlib import Path
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
from astropy.io import fits
import pandas as pd
import requests

import revised_pilot as previous
import search

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/coverage_pilot"
EXTRA = ROOT / "data/coverage_lightcurves"
sha, save = previous.sha, previous.save


def verify_plan():
    plan = json.loads((REPORT / "plan.json").read_text())
    for name, digest in plan["source_sha256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Frozen source changed: " + name)
    for row in plan["targets"]:
        actual = {
            str(p.relative_to(ROOT))
            for p in (ROOT / "data/lightcurves" / str(row["tic"])).glob("*_lc.fits")
        }
        expected = {p["path"] for p in row["original_products"]}
        if actual != expected:
            raise ValueError("Original product set changed: " + str(row["tic"]))
        for record in row["original_products"]:
            if sha(ROOT / record["path"]) != record["sha256"]:
                raise ValueError("Original product changed: " + record["path"])
    return plan


def prepare():
    REPORT.mkdir(exist_ok=True)
    if (REPORT / "plan.json").exists():
        plan = verify_plan()
        print("Existing plan verified", len(plan["targets"]))
        return
    prerequisite, _ = previous.prepare()
    if prerequisite["method"] != "coarse_only":
        raise ValueError("Expected the independently selected simpler revision")
    inventory_path = ROOT / "reports/unused_coverage/inventory.json"
    inventory = json.loads(inventory_path.read_text())
    if inventory["errors"]:
        raise ValueError("Resolve inventory errors before selecting targets")
    targets = []
    for rank, row in enumerate(inventory["rows"][:20], 1):
        tic = row["tic"]
        if (
            any((EXTRA / str(tic)).glob("*_lc.fits"))
            or (ROOT / "results" / f"{tic}_coverage_pilot").exists()
        ):
            raise ValueError("New data or output exists before first preparation")
        for field, digest in [
            ("catalogue_source", "catalogue_sha256"),
            ("noise_source", "noise_source_sha256"),
        ]:
            if sha(ROOT / row[field]) != row[digest]:
                raise ValueError("Inventory input changed: " + row[field])
        records = []
        for path in sorted((ROOT / "data/lightcurves" / str(tic)).glob("*_lc.fits")):
            with fits.open(path, memmap=True) as h:
                assert int(h[0].header["TICID"]) == tic
                sector = int(h[0].header["SECTOR"])
            records.append(
                dict(
                    path=str(path.relative_to(ROOT)),
                    sector=sector,
                    bytes=path.stat().st_size,
                    sha256=sha(path),
                )
            )
        assert sorted(r["sector"] for r in records) == row["old_sectors"]
        assert len({r["sector"] for r in row["unused_products"]}) == len(row["unused_products"])
        assert {r["sector"] for r in row["unused_products"]}.isdisjoint(row["old_sectors"])
        targets.append(dict(rank=rank, **row, original_products=records))
    assert len(targets) == 20 and sum(len(r["unused_products"]) for r in targets) == 390
    sources = dict(prerequisite["source_sha256"])
    for path in [
        Path(__file__),
        ROOT / "docs/COVERAGE_PILOT.md",
        inventory_path,
        ROOT / "scripts/inventory_unused_coverage.py",
    ]:
        sources[str(path.relative_to(ROOT))] = sha(path)
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        method="coarse_only",
        source_sha256=sources,
        targets=targets,
        original_products=sum(len(r["original_products"]) for r in targets),
        additional_products=sum(len(r["unused_products"]) for r in targets),
        maximum_retained_fits=2,
        bls_threads_per_call=2,
        selection="First 20 ranked rows of the published unused-coverage inventory, unchanged. No new flux used for selection.",
        scope="Exploratory expanded-coverage reanalysis of previously searched stars. Original and new sector sets are disjoint. Combine them before unchanged per-sector preprocessing and the original whole-sector training/holdout split. Freeze training fits before inspecting this run's holdout; some old sectors were examined previously. This is not independent population validation, adoption of the failed shortlist variants, a novel method or a planet claim.",
    )
    save(REPORT / "plan.json", plan)
    print(
        json.dumps(
            dict(
                targets=len(targets),
                original=plan["original_products"],
                additional=plan["additional_products"],
                method=plan["method"],
            )
        )
    )


def download_one(tic, product):
    folder = EXTRA / str(tic)
    folder.mkdir(parents=True, exist_ok=True)
    name = product["filename"]
    if Path(name).name != name or not name.endswith("_lc.fits"):
        raise ValueError("Unexpected product filename")
    path = folder / name
    if not path.exists():
        for attempt in range(2):
            try:
                response = requests.get(
                    "https://mast.stsci.edu/api/v0.1/Download/file",
                    params={"uri": product["uri"]},
                    timeout=(15, 100),
                )
                response.raise_for_status()
                if not response.content.startswith(b"SIMPLE"):
                    raise ValueError("Archive response is not FITS")
                temporary = path.with_suffix(".part")
                temporary.write_bytes(response.content)
                with fits.open(temporary, memmap=True) as h:
                    assert int(h[0].header["TICID"]) == tic
                    assert int(h[0].header["SECTOR"]) == product["sector"]
                temporary.replace(path)
                break
            except Exception:
                if attempt == 1:
                    raise
                time.sleep(2)
    with fits.open(path, memmap=True) as h:
        assert int(h[0].header["TICID"]) == tic
        assert int(h[0].header["SECTOR"]) == product["sector"]
    return dict(
        tic=tic,
        **product,
        path=str(path.relative_to(ROOT)),
        bytes=path.stat().st_size,
        sha256=sha(path),
    )


def download():
    plan = verify_plan()
    manifest_path = REPORT / "download_manifest.json"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text())
        for row in prior["files"]:
            if sha(ROOT / row["path"]) != row["sha256"]:
                raise ValueError("Previously downloaded file changed")
    rows, errors = [], []
    state = dict(
        started_utc=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(REPORT / "plan.json"),
        files=rows,
        errors=errors,
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {
            pool.submit(download_one, target["tic"], p): (target["tic"], p)
            for target in plan["targets"]
            for p in target["unused_products"]
        }
        for job in as_completed(jobs):
            tic, product = jobs[job]
            try:
                rows.append(job.result())
            except Exception as exc:
                errors.append(dict(tic=tic, sector=product["sector"], error=repr(exc)))
            if (len(rows) + len(errors)) % 10 == 0 or errors:
                state["updated_utc"] = datetime.now(timezone.utc).isoformat()
                save(REPORT / "download_progress.json", state)
                print(
                    json.dumps(dict(downloaded=len(rows), total=len(jobs), errors=len(errors))),
                    flush=True,
                )
    rows.sort(key=lambda r: (r["tic"], r["sector"]))
    state.update(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        complete=not errors and len(rows) == plan["additional_products"],
    )
    save(manifest_path, state)
    if not state["complete"]:
        raise ValueError("Incomplete download; inspect errors and preserve successful files")


def load_coverage(tic):
    source = inspect.getsource(search.load_target)
    old = 'ROOT / "data/lightcurves" / str(tic)'
    assert source.count(old) == 1
    namespace = dict(vars(search))
    exec(
        compile(
            source.replace(old, 'ROOT / "data/coverage_lightcurves" / str(tic)'),
            "<additional-coverage-loader>",
            "exec",
        ),
        namespace,
    )
    original, old_meta = search.load_target(tic)
    added, new_meta = namespace["load_target"](tic)
    assert set(original.sector).isdisjoint(added.sector)
    combined = (
        pd.concat([original, added], ignore_index=True).sort_values("time").reset_index(drop=True)
    )
    assert not combined.time.duplicated().any()
    return combined, old_meta + new_meta


def adapted_functions():
    namespace = dict(vars(previous), load_target=load_coverage)
    for function in [previous.checked_cache, previous.worker]:
        source = inspect.getsource(function)
        assert source.count("_revised_pilot") == 1
        source = source.replace("_revised_pilot", "_coverage_pilot")
        exec(compile(source, "<full-coverage-worker>", "exec"), namespace)
    return namespace


def worker(tic, method, execution_hash):
    return adapted_functions()["worker"](tic, method, execution_hash)


def run(workers):
    plan = verify_plan()
    manifest = json.loads((REPORT / "download_manifest.json").read_text())
    assert manifest["complete"] and not manifest["errors"]
    assert manifest["plan_sha256"] == sha(REPORT / "plan.json")
    assert len(manifest["files"]) == plan["additional_products"]
    for target in plan["targets"]:
        actual = {p.name for p in (EXTRA / str(target["tic"])).glob("*_lc.fits")}
        assert actual == {p["filename"] for p in target["unused_products"]}
    for record in manifest["files"]:
        assert sha(ROOT / record["path"]) == record["sha256"]
    execution = dict(
        selection_plan_sha256=sha(REPORT / "plan.json"),
        download_manifest_sha256=sha(REPORT / "download_manifest.json"),
        method=plan["method"],
        targets=[r["tic"] for r in plan["targets"]],
        input_products=plan["original_products"] + plan["additional_products"],
    )
    execution_path = REPORT / "execution_plan.json"
    if execution_path.exists():
        old = json.loads(execution_path.read_text())
        assert all(old[k] == v for k, v in execution.items())
    else:
        save(execution_path, dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **execution))
    execution_hash = sha(execution_path)
    cache = adapted_functions()["checked_cache"]
    rows, pending = [], []
    for tic in execution["targets"]:
        receipt = cache(tic, execution_hash)
        if receipt:
            rows.append(receipt)
        else:
            pending.append(tic)
    state = dict(
        started_utc=datetime.now(timezone.utc).isoformat(),
        selection_plan_sha256=execution["selection_plan_sha256"],
        execution_plan_sha256=execution_hash,
        selected=len(execution["targets"]),
        method=plan["method"],
        workers=workers,
        rows=rows,
        errors=[],
    )

    def checkpoint():
        state.update(updated_utc=datetime.now(timezone.utc).isoformat(), completed=len(rows))
        save(REPORT / "progress.json", state)

    checkpoint()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(worker, tic, plan["method"], execution_hash): tic for tic in pending}
        for job in as_completed(jobs):
            try:
                row = job.result()
                rows.append(row)
                print(
                    json.dumps(
                        {k: row[k] for k in ["tic", "fits", "unflagged", "elapsed_seconds"]}
                    ),
                    flush=True,
                )
            except Exception as exc:
                error = dict(tic=jobs[job], error=repr(exc))
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
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["prepare", "download", "run"])
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.workers < 1 or args.workers * 2 > (os.cpu_count() or 1):
        parser.error("Workers must fit two BLS threads each within the CPU count")
    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs/coverage_pilot.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.operation == "prepare":
            prepare()
        elif args.operation == "download":
            download()
        else:
            run(args.workers)
