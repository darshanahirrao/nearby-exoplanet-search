"""Compare complete combined-season outputs and wall time on saved real inputs.

Both runs use the same data and unchanged search_combined implementation. Timing
is descriptive on the current machine/load; the adapter is rejected on any
numerical or screening difference. Existing research results are never replaced.
"""

import argparse
from datetime import datetime, timezone
from functools import partial
import hashlib
import json
from pathlib import Path
import platform
import tempfile
import time
import astropy
import pandas as pd
import longbaseline
from parallel_bls import ParallelBoxLeastSquares

ROOT = Path(__file__).resolve().parents[1]


def science(result):
    return {
        key: value for key, value in result.items() if key not in {"elapsed_seconds", "frozen_utc"}
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tics", nargs="+", type=int, required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    report = dict(
        started_utc=datetime.now(timezone.utc).isoformat(),
        threads=args.threads,
        platform=platform.platform(),
        astropy=astropy.__version__,
        adapter_sha256=hashlib.sha256((ROOT / "scripts/parallel_bls.py").read_bytes()).hexdigest(),
        trials=[],
        limitations="Small real-input timing comparison under concurrent machine load, not a hardware-independent speed guarantee or an astrophysical validation.",
    )
    original = longbaseline.BoxLeastSquares
    for tic in args.tics:
        source = ROOT / "results" / f"{tic}_longbaseline"
        prior = json.loads((source / "result.json").read_text())
        frame = source / "lightcurve.csv.gz"
        if not frame.exists():
            # The TOI-700 control predates processed-frame preservation.
            frame = ROOT / "results" / f"{tic}_calibration_v2" / "lightcurve.csv.gz"
            data, _ = longbaseline.clean_variability(pd.read_csv(frame), pd.Series(prior["star"]))
        else:
            data = pd.read_csv(frame)
        outputs, seconds = {}, {}
        # Alternate order to reduce a systematic warm-up advantage.
        modes = ["serial", "parallel"] if len(report["trials"]) % 2 == 0 else ["parallel", "serial"]
        for mode in modes:
            longbaseline.BoxLeastSquares = (
                original
                if mode == "serial"
                else partial(ParallelBoxLeastSquares, threads=args.threads)
            )
            with tempfile.TemporaryDirectory(prefix="bls-benchmark-") as folder:
                start = time.perf_counter()
                outputs[mode] = science(
                    longbaseline.search_combined(data, pd.Series(prior["star"]), folder)
                )
                seconds[mode] = time.perf_counter() - start
        identical = outputs["serial"] == outputs["parallel"]
        row = dict(
            tic=tic,
            points=len(data),
            source_sha256=hashlib.sha256(frame.read_bytes()).hexdigest(),
            seconds=seconds,
            speedup=seconds["serial"] / seconds["parallel"],
            entire_scientific_result_identical=identical,
            serial_periods=[s["period_days"] for s in outputs["serial"].get("signals", [])],
        )
        report["trials"].append(row)
        print(json.dumps(row), flush=True)
        if not identical:
            report["mismatch"] = {key: outputs[key] for key in outputs}
            break
    longbaseline.BoxLeastSquares = original
    report["all_identical"] = all(
        row["entire_scientific_result_identical"] for row in report["trials"]
    )
    report["completed_utc"] = datetime.now(timezone.utc).isoformat()
    report["aggregate_speedup"] = sum(r["seconds"]["serial"] for r in report["trials"]) / sum(
        r["seconds"]["parallel"] for r in report["trials"]
    )
    dest = ROOT / "reports/performance"
    dest.mkdir(exist_ok=True)
    (dest / "parallel_bls.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["all_identical"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
