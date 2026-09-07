"""Recheck real, catalogued TOI-700 signals with the frozen pipeline revisions."""

from datetime import datetime, timezone
from functools import partial
import hashlib
import json
from pathlib import Path
import time

import pandas as pd

from cycle_excluded import PRODUCTION_CLEAN
import longbaseline
from multimode_cycle_experiment import weak
from parallel_bls import ParallelBoxLeastSquares
from physical_duration import PhysicalDurationBLS
import qualified_seeds

ROOT = Path(__file__).resolve().parents[1]
METHODS = ["production", "harmonic_three", "coarse_only", "qualified_seeds"]


def main():
    out = ROOT / "reports/calibration/revised_pipeline"
    out.mkdir(parents=True, exist_ok=True)
    lc_path = ROOT / "results/150428135_calibration_v2/lightcurve.csv.gz"
    star_path = ROOT / "results/150428135_calibration_v2/result.json"
    catalogue_path = ROOT / "data/catalogs/exofop_toi.csv"
    previous_path = ROOT / "reports/calibration/150428135_longbaseline.json"
    previous = json.loads(previous_path.read_text())
    input_hash = hashlib.sha256(lc_path.read_bytes()).hexdigest()
    if previous["source_sha256"] != input_hash:
        raise ValueError("Corrected TOI-700 calibration input changed")
    star = pd.Series(json.loads(star_path.read_text())["star"])
    catalogue = pd.read_csv(catalogue_path)
    catalogue = catalogue[pd.to_numeric(catalogue["TIC ID"], errors="coerce") == 150428135]
    truth = [
        dict(
            toi=float(r["TOI"]),
            period_days=float(r["Period (days)"]),
            epoch_btjd=float(r["Epoch (BJD)"] - 2457000),
            duration_days=float(r["Duration (hours)"] / 24),
        )
        for _, r in catalogue.iterrows()
    ]
    prior = json.loads((ROOT / "reports/experiments/pipeline_confirmation/plan.json").read_text())
    files = list(prior["source_sha256"]) + [
        "docs/CALIBRATION_REVISED_PIPELINE.md",
        "scripts/pipeline_control.py",
    ]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    if any(hashes[p] != digest for p, digest in prior["source_sha256"].items()):
        raise ValueError("A frozen revision changed")
    path = out / "plan.json"
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        methods=METHODS,
        source_sha256=hashes,
        input_sha256={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [lc_path, star_path, catalogue_path, previous_path]
        },
        catalogue_truth=truth,
        bls_threads=1,
        scope="Previously inspected real known-planet control; not independent selection or discovery.",
    )
    if path.exists():
        old = json.loads(path.read_text())
        if any(
            old[k] != plan[k]
            for k in ["source_sha256", "input_sha256", "catalogue_truth", "bls_threads"]
        ):
            raise ValueError("Preserve the frozen control")
        plan = old
    else:
        path.write_text(json.dumps(plan, indent=2) + "\n")
    original = pd.read_csv(lc_path)
    longbaseline.BoxLeastSquares = partial(ParallelBoxLeastSquares, threads=1)
    qualified_seeds.ParallelBoxLeastSquares = partial(ParallelBoxLeastSquares, threads=1)
    qualified_seeds.PhysicalDurationBLS = partial(PhysicalDurationBLS, threads=1)
    rows = []
    for method in METHODS:
        folder = out / method
        folder.mkdir(exist_ok=True)
        result_path = folder / "result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text())
        else:
            start = time.monotonic()
            df, models = (PRODUCTION_CLEAN if method == "production" else weak)(
                original.copy(), star
            )
            search = (
                qualified_seeds.ORIGINAL_SEARCH
                if method in METHODS[:2]
                else qualified_seeds.make_search(qualified=method == "qualified_seeds")
            )
            result = search(df, star, folder)
            result.update(
                method=method,
                source_sha256=input_hash,
                star=star.to_dict(),
                variability_models=models,
                total_elapsed_seconds=time.monotonic() - start,
            )
            result_path.write_text(json.dumps(result, indent=2) + "\n")
        training, _ = longbaseline.sector_split(original)
        matches = []
        for signal in result["signals"]:
            for known in truth:
                period, epoch = signal["period_days"], signal["epoch_btjd"]
                drift = []
                for t in [training.time.min(), training.time.max()]:
                    center = epoch + round((t - epoch) / period) * period
                    drift.append(
                        float(
                            abs(
                                (center - known["epoch_btjd"] + known["period_days"] / 2)
                                % known["period_days"]
                                - known["period_days"] / 2
                            )
                        )
                    )
                if (
                    abs(period / known["period_days"] - 1) < 0.001
                    and max(drift) < 0.75 * known["duration_days"]
                ):
                    strict = bool(
                        signal["nominal_training_snr"] >= 7
                        and signal["discovery"]["n_observed_events"] >= 3
                        and signal["holdout"]["n_observed_events"] >= 2
                        and (signal["holdout"]["fixed_ephemeris_snr"] or 0) >= 5
                    )
                    matches.append(
                        dict(
                            toi=known["toi"],
                            period_days=period,
                            edge_timing_errors_days=drift,
                            strict=strict,
                            all_screening_checks=not signal["screening_flags"],
                        )
                    )
        row = dict(
            method=method,
            matches=matches,
            periods=[s["period_days"] for s in result["signals"]],
            total_elapsed_seconds=result["total_elapsed_seconds"],
            result_path=str(result_path.relative_to(ROOT)),
            result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(),
        )
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / "results.json").write_text(
        json.dumps(dict(completed_utc=datetime.now(timezone.utc).isoformat(), rows=rows), indent=2)
        + "\n"
    )


if __name__ == "__main__":
    main()
