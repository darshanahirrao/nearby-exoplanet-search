"""Resume the unchanged combined-season search with checked caches and threaded BLS.

Only scheduling changes. This runner must not overlap the original longbaseline
runner, whose historical version has no shared lock. Use a separate process after
the old run has stopped; completed result files are preserved byte-for-byte.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import time

# Set before importing numerical packages and inherited by spawned workers.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import longbaseline
from parallel_bls import ParallelBoxLeastSquares

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_cache(tic):
    folder = ROOT / "results" / f"{tic}_longbaseline"
    path = folder / "result.json"
    if not path.exists():
        return False
    result = json.loads(path.read_text())
    if result.get("tic") != tic or result.get("status") not in {
        "longbaseline_screened",
        "skipped_fewer_than_three_sectors",
        "skipped_no_period_range",
    }:
        raise ValueError(f"Invalid cached result for TIC {tic}")
    for source, key in [
        (ROOT / result["source_data"], "source_sha256"),
        (folder / "lightcurve.csv.gz", "processed_data_sha256"),
    ]:
        if sha(source) != result[key]:
            raise ValueError(f"Cached data hash mismatch for TIC {tic}: {key}")
    if result.get("signals"):
        frozen = json.loads((folder / "frozen_training.json").read_text())
        fields = ("period_days", "epoch_btjd", "duration_days", "depth")
        if len(frozen["signals"]) != len(result["signals"]) or any(
            any(old[key] != final[key] for key in fields)
            for old, final in zip(frozen["signals"], result["signals"])
        ):
            raise ValueError(f"Frozen-result mismatch for TIC {tic}")
    return True


def worker(tic, threads):
    longbaseline.BoxLeastSquares = partial(ParallelBoxLeastSquares, threads=threads)
    result = longbaseline.process_target(tic)
    result["execution_adapter"] = dict(
        name="parallel_bls",
        threads=threads,
        adapter_sha256=sha(ROOT / "scripts/parallel_bls.py"),
        runner_sha256=sha(Path(__file__)),
        scientific_grid_and_thresholds="unchanged",
    )
    path = ROOT / "results" / f"{tic}_longbaseline" / "result.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2))
    temporary.replace(path)
    return dict(
        tic=tic,
        status=result["status"],
        elapsed_seconds=result.get("elapsed_seconds", 0),
        unflagged=sum(not s["screening_flags"] for s in result["signals"]),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tics", nargs="+", type=int)
    parser.add_argument("--all-screened", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1 or args.threads < 1 or args.workers * args.threads > (os.cpu_count() or 1):
        parser.error("Use positive worker/thread counts within the logical CPU count")
    tics = set(args.tics or [])
    if args.all_screened:
        tics.update(
            int(p.parent.name)
            for p in (ROOT / "results").glob("*/result.json")
            if p.parent.name.isdigit() and p.parent.name != "150428135"
        )
    if not tics:
        parser.error("Select targets")
    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs/accelerated_longbaseline.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cached = [tic for tic in sorted(tics) if checked_cache(tic)]
        pending = list(tics - set(cached))
        # Start larger input frames first to reduce a long single-worker tail.
        pending.sort(
            key=lambda tic: (
                (ROOT / "results" / f"{tic}_variability" / "lightcurve.csv.gz").stat().st_size
            ),
            reverse=True,
        )
        state = dict(
            started_utc=datetime.now(timezone.utc).isoformat(),
            selected=len(tics),
            checked_cached=len(cached),
            pending_at_start=pending,
            workers=args.workers,
            threads_per_worker=args.threads,
            runner_sha256=sha(Path(__file__)),
            completed=[],
            errors=[],
        )
        state_path = ROOT / "logs/accelerated_longbaseline.json"

        def save():
            state["updated_utc"] = datetime.now(timezone.utc).isoformat()
            temporary = state_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(state, indent=2))
            temporary.replace(state_path)

        save()
        print(
            json.dumps(
                {
                    k: state[k]
                    for k in ["selected", "checked_cached", "workers", "threads_per_worker"]
                }
            ),
            flush=True,
        )
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(worker, tic, args.threads): tic for tic in pending}
            for future in as_completed(futures):
                tic = futures[future]
                try:
                    row = future.result()
                    state["completed"].append(row)
                    print(json.dumps(row), flush=True)
                except Exception as exc:
                    row = dict(tic=tic, error=repr(exc))
                    state["errors"].append(row)
                    print(json.dumps(row), flush=True)
                save()
        state["elapsed_seconds"] = time.monotonic() - start
        state["status"] = "error" if state["errors"] else "finished"
        save()
        if state["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
