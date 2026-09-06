"""Export auditable, compact research records without committing raw downloads."""

from datetime import datetime, timezone
import json, shutil, hashlib
import pandas as pd
from search import ROOT


def main():
    reports = ROOT / "reports"
    provenance = ROOT / "provenance"
    for p in [reports / "tables", reports / "calibration", provenance]:
        p.mkdir(parents=True, exist_ok=True)
    target_rows = []
    signal_rows = []
    refined_rows = []
    observations = []
    refinement_attempts = 0
    for source in sorted((ROOT / "results").glob("*/result.json")):
        if not source.parent.name.isdigit() or source.parent.name == "150428135":
            continue
        r = json.loads(source.read_text())
        tic = r["tic"]
        target_rows.append(
            dict(
                tic=tic,
                status=r["status"],
                period_grid_searched=bool(r.get("search_config")),
                sectors=len(r.get("files", [])),
                points=r.get("points"),
                discovery_points=r.get("discovery_points"),
                holdout_points=r.get("validation_points"),
                tmag=r.get("star", {}).get("Tmag"),
                distance_pc=r.get("star", {}).get("Dist"),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            )
        )
        for s in r.get("signals", []):
            signal_rows.append(
                dict(
                    tic=tic,
                    iteration=s["iteration"],
                    period_days=s["period_days"],
                    epoch_btjd=s["epoch_btjd"],
                    duration_days=s["duration_days"],
                    depth=s["depth"],
                    radius_earth_estimate=s["radius_earth_estimate"],
                    irradiation_earth_estimate=s["irradiation_earth_estimate"],
                    nominal_snr=s["nominal_bls_snr"],
                    holdout_nominal_snr=s["validation"]["fixed_ephemeris_snr"],
                    flags=";".join(s["screening_flags"]),
                )
            )
        refined = source.parent.with_name(source.parent.name + "_refined") / "result.json"
        if refined.exists():
            refinement_attempts += 1
            f = json.loads(refined.read_text())
            for s in f["signals"]:
                disposition = reports / "vetting" / str(tic) / "disposition.json"
                note = (
                    json.loads(disposition.read_text()).get("disposition", "")
                    if disposition.exists()
                    else ""
                )
                refined_rows.append(
                    dict(
                        tic=tic,
                        seed_iteration=s["seed_iteration"],
                        period_days=s["period_days"],
                        epoch_btjd=s["epoch_btjd"],
                        duration_days=s["duration_days"],
                        depth=s["depth"],
                        radius_earth_estimate=s["radius_earth_estimate"],
                        irradiation_earth_estimate=s["irradiation_earth_estimate"],
                        nominal_training_snr=s["nominal_training_snr"],
                        holdout_nominal_snr=s["holdout"]["fixed_ephemeris_snr"],
                        holdout_events=s["holdout"]["n_observed_events"],
                        flags=";".join(s["screening_flags"]),
                        target_vetting_note=note,
                    )
                )
        obs = ROOT / "data/download_status" / f"{tic}.json"
        if obs.exists():
            o = json.loads(obs.read_text())
            observations.append(dict(tic=tic, state=o["state"], files=o.get("files", [])))
    pd.DataFrame(target_rows).to_csv(reports / "tables/targets.csv", index=False)
    pd.DataFrame(signal_rows).to_csv(reports / "tables/initial_screening.csv", index=False)
    pd.DataFrame(refined_rows).to_csv(reports / "tables/refined_screening.csv", index=False)
    (provenance / "observations.json").write_text(json.dumps(observations, indent=2))
    experiments = []
    for folder in sorted((ROOT / "results").glob("injections*")):
        plan = folder / "plan.json"
        if not plan.exists():
            continue
        dest = reports / "calibration" / folder.name
        dest.mkdir(exist_ok=True)
        shutil.copyfile(plan, dest / "plan.json")
        rows = []
        for file in sorted(folder.glob("*/result.json")):
            r = json.loads(file.read_text())
            rows.append(
                {
                    k: r.get(k)
                    for k in [
                        "id",
                        "tic",
                        "seed",
                        "period_days",
                        "epoch_btjd",
                        "radius_earth",
                        "depth",
                        "duration_days",
                        "status",
                        "recovered_in_top3",
                        "recovered_with_strict_holdout",
                        "elapsed_seconds",
                    ]
                }
            )
        pd.DataFrame(rows).to_csv(dest / "recovery.csv", index=False)
        experiments.append(
            dict(
                suite=folder.name,
                finished=len(rows),
                recovered=sum(bool(x["recovered_in_top3"]) for x in rows),
                strict_holdout=sum(bool(x["recovered_with_strict_holdout"]) for x in rows),
            )
        )
    for name in ["150428135_calibration_v2", "150428135_calibration_v2_refined"]:
        p = ROOT / "results" / name / "result.json"
        if p.exists():
            shutil.copyfile(p, reports / "calibration" / f"{name}.json")
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(
        updated_utc=now,
        processed_targets=len(target_rows),
        period_searched_targets=sum(r["period_grid_searched"] for r in target_rows),
        initial_trial_fits=len(signal_rows),
        refinement_attempts=refinement_attempts,
        refined_targets_with_trial_fits=len({r["tic"] for r in refined_rows}),
        initial_unflagged=sum(not r["flags"] for r in signal_rows),
        refined_unflagged=sum(not r["flags"] for r in refined_rows),
        confirmed_new_planets=0,
        experiments=experiments,
        claims="Screening and calibration results only. Unflagged does not mean validated. Consult individual vetting records.",
    )
    (reports / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
