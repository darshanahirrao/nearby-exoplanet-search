"""Bounded additional-planet search around confirmed-planet hosts.

Remove catalogued TOI transit windows, then use the unchanged combined-season
search. Masks, source files and code hashes are retained. Results are exploratory,
and period/harmonic matches still require event-level inspection.
"""

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from search import ROOT, load_target, mask_known_inner, known_matches
from variability import clean_variability
from longbaseline import search_combined


def process(tic):
    folder = ROOT / "results" / f"{tic}_known_residual"
    result_file = folder / "result.json"
    if result_file.exists():
        return json.loads(result_file.read_text())
    folder.mkdir(exist_ok=True)
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    star = stars.loc[tic]
    curve, files = load_target(tic)
    before = len(curve)
    curve, masks = mask_known_inner(curve, tic, float("inf"))
    curve, models = clean_variability(curve, star)
    curve.to_csv(folder / "lightcurve.csv.gz", index=False)
    result = search_combined(curve, star, folder)
    for signal in result["signals"]:
        signal["known_matches"] = known_matches(tic, signal["period_days"])
        if signal["known_matches"]:
            signal["screening_flags"].append("known_period_or_harmonic_requires_ephemeris_review")
    result.update(
        tic=tic,
        star=star.to_dict(),
        files=files,
        known_transit_masks=masks,
        masked_points=before - len(curve),
        variability_models=models,
        processed_data_sha256=hashlib.sha256(
            (folder / "lightcurve.csv.gz").read_bytes()
        ).hexdigest(),
        code_sha256={
            name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in [
                "known_residual.py",
                "search.py",
                "variability.py",
                "longbaseline.py",
                "physics.py",
            ]
        },
        claims="Additional-planet exploratory search with known TOI transit windows masked. No new planet claimed.",
    )
    result_file.write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    plan_path = ROOT / "provenance" / "known_host_search_plan.json"
    if not plan_path.exists():
        targets = pd.read_csv(ROOT / "data/catalogs/ranked_targets.csv")
        planets = pd.read_csv(ROOT / "data/catalogs/confirmed_planets.csv")
        ids = (
            pd.to_numeric(
                planets.tic_id.astype(str).str.replace("TIC ", "", regex=False), errors="coerce"
            )
            .dropna()
            .astype(int)
        )
        targets = targets[targets.TIC.isin(ids)]
        plan = dict(
            created_utc=datetime.now(timezone.utc).isoformat(),
            selection="All ranked eligible catalogue stars with a confirmed-planet TIC match; fixed before this residual search. Some also occur in the main tranche.",
            targets=targets.TIC.astype(int).tolist(),
        )
        plan_path.write_text(json.dumps(plan, indent=2))
    plan = json.loads(plan_path.read_text())
    if args.prepare:
        print("Prepared", len(plan["targets"]), "hosts")
        return
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(process, tic): tic for tic in plan["targets"]}
        for job in as_completed(jobs):
            try:
                result = job.result()
                print(
                    result["tic"],
                    result["status"],
                    "unflagged",
                    sum(not s["screening_flags"] for s in result["signals"]),
                    flush=True,
                )
            except Exception as exc:
                print(jobs[job], "error", repr(exc), flush=True)


if __name__ == "__main__":
    main()
