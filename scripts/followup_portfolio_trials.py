"""Fresh archived-sector checks of two fixed TIC 233738219 ephemerides.

Prepare and publish the plan before downloading any selected flux. This is a
single-star follow-up, not adoption of a failed experimental search method.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.table import Table

from local_baseline import continuum_train
from multimode_cycle_experiment import weak
from repeated_events import EventContrasts
import search
from vet import folded_panel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/vetting/fresh_sector_followup"
DATA = ROOT / "data/followup_lightcurves/233738219"
TIC = 233738219


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "plan.json").exists():
        verify_plan()
        print("Existing frozen plan verified; no flux downloaded")
        return
    if DATA.exists() and any(DATA.glob("*_lc.fits")):
        raise ValueError("Fresh-sector flux already present; cannot claim pre-download preparation")
    old = sorted((ROOT / "data/lightcurves" / str(TIC)).glob("*_lc.fits"))
    old_sectors = set()
    for p in old:
        with fits.open(p, memmap=True) as h:
            assert int(h[0].header["TICID"]) == TIC
            old_sectors.add(int(h[0].header["SECTOR"]))
    catalog_path = ROOT / "data/products/233738219.ecsv"
    products = Table.read(catalog_path)
    selected = []
    for row in products:
        sector = int(row["sequence_number"])
        if sector in old_sectors:
            continue
        assert str(row["author"]) == "SPOC" and float(row["exptime"]) == 120
        name = str(row["productFilename"])
        assert Path(name).name == name and name.endswith("_lc.fits")
        selected.append(
            dict(
                sector=sector,
                filename=name,
                uri=str(row["dataURI"]),
                observation_start_mjd=float(row["t_min"]),
                observation_end_mjd=float(row["t_max"]),
            )
        )
    selected.sort(key=lambda r: r["sector"])
    assert len({p["sector"] for p in selected}) == len(selected) and len(selected) > 0
    queue_path = ROOT / "reports/experiments/portfolio/unmodified_review_queue.json"
    queue = json.loads(queue_path.read_text())["trials"]
    signals = []
    for trial in sorted(queue, key=lambda r: r["method"] != "leave_one_out"):
        source = ROOT / trial["result_path"]
        assert sha(source) == trial["result_sha256"]
        signals.append(
            dict(
                role="primary" if trial["method"] == "leave_one_out" else "comparison",
                method=trial["method"],
                source=trial["result_path"],
                source_sha256=sha(source),
                **{k: trial["signal"][k] for k in ["period_days", "epoch_btjd", "duration_days"]},
            )
        )
    helpers = [
        "followup_portfolio_trials.py",
        "local_baseline.py",
        "search.py",
        "physics.py",
        "variability.py",
        "cycle_excluded.py",
        "multimode_cycle_experiment.py",
        "repeated_events.py",
        "vet.py",
    ]
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        tic=TIC,
        selected_products=selected,
        original_sectors=sorted(old_sectors),
        signals=signals,
        source_sha256={name: sha(ROOT / "scripts" / name) for name in helpers},
        previous_input_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in old + [catalog_path, queue_path, ROOT / "data/catalogs/all_hz_targets.csv"]
        },
        selection_rule="Every unused sector in the project's existing 120-second SPOC product-table snapshot, excluding the 18 sectors already downloaded. Selection uses only identifiers and metadata; no selected flux has been downloaded in this project.",
        checks=dict(
            minimum_measurable_events=3,
            minimum_positive_fraction=0.6,
            minimum_nominal_pdc_snr=5,
            quadratic_degree=2,
            quadratic_width_scale=1.0,
        ),
        scope="A fixed-ephemeris single-star follow-up using previously unexamined archived sectors. Primary period is 26.316459 days; the other trial is a disclosed comparison. No period/epoch/duration refinement or new long-period search. Report PDC and SAP, before and after the frozen three-pass harmonic filter, original and two-sided quadratic event statistics, and every rotation phase class (divisor nearest period/1.316 days). The stated recurrence screen requires event count, positive fraction and nominal SNR in both original and quadratic PDC statistics after filtering. This is not calibrated planet validation or permission to adopt the failed survey method.",
    )
    write(OUT / "plan.json", plan)
    print("Plan frozen before download:", len(selected), "sectors", [p["sector"] for p in selected])


def verify_plan():
    plan = json.loads((OUT / "plan.json").read_text())
    for name, digest in plan["source_sha256"].items():
        assert sha(ROOT / "scripts" / name) == digest, name
    for name, digest in plan["previous_input_sha256"].items():
        assert sha(ROOT / name) == digest, name
    return plan


def download_one(product):
    path = DATA / product["filename"]
    if not path.exists():
        response = requests.get(
            "https://mast.stsci.edu/api/v0.1/Download/file",
            params={"uri": product["uri"]},
            timeout=(15, 100),
        )
        response.raise_for_status()
        if not response.content.startswith(b"SIMPLE"):
            raise ValueError("Archive response is not a FITS primary HDU")
        temporary = path.with_suffix(".part")
        temporary.write_bytes(response.content)
        with fits.open(temporary, memmap=True) as h:
            assert int(h[0].header["TICID"]) == TIC
            assert int(h[0].header["SECTOR"]) == product["sector"]
        temporary.replace(path)
    with fits.open(path, memmap=False) as h:
        assert int(h[0].header["TICID"]) == TIC
        assert int(h[0].header["SECTOR"]) == product["sector"]
        time = np.asarray(h[1].data["TIME"], dtype=float)
        finite = time[np.isfinite(time)]
        assert len(finite) > 100 and np.all(np.diff(finite) > 0)
    return dict(
        **product,
        path=str(path.relative_to(ROOT)),
        sha256=sha(path),
        bytes=path.stat().st_size,
        first_time_btjd=float(finite[0]),
        last_time_btjd=float(finite[-1]),
    )


def download():
    plan = verify_plan()
    DATA.mkdir(parents=True, exist_ok=True)
    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(download_one, p): p for p in plan["selected_products"]}
        for job in as_completed(jobs):
            product = jobs[job]
            try:
                row = job.result()
                rows.append(row)
                print("Downloaded", len(rows), "/", len(jobs), "sector", row["sector"], flush=True)
            except Exception as exc:
                errors.append(dict(sector=product["sector"], error=repr(exc)))
    write(
        OUT / "download_manifest.json",
        dict(
            completed_utc=datetime.now(timezone.utc).isoformat(),
            plan_sha256=sha(OUT / "plan.json"),
            files=sorted(rows, key=lambda r: r["sector"]),
            errors=errors,
        ),
    )
    if errors or len(rows) != len(plan["selected_products"]):
        raise ValueError("Incomplete download; preserve successful files and retry download")


def followup_loader():
    source = inspect.getsource(search.load_target)
    old = 'ROOT / "data/lightcurves" / str(tic)'
    assert source.count(old) == 1
    source = source.replace(old, 'ROOT / "data/followup_lightcurves" / str(tic)')
    namespace = dict(vars(search))
    exec(compile(source, "<separate-followup-directory>", "exec"), namespace)
    return namespace["load_target"]


def analyze():
    plan = verify_plan()
    manifest = json.loads((OUT / "download_manifest.json").read_text())
    assert manifest["plan_sha256"] == sha(OUT / "plan.json") and not manifest["errors"]
    expected = {r["filename"] for r in plan["selected_products"]}
    assert {p.name for p in DATA.glob("*_lc.fits")} == expected
    assert {r["filename"] for r in manifest["files"]} == expected
    for row in manifest["files"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    frames, model_records = {}, {}
    original_times, _ = search.load_target(TIC)
    for flux in ["PDCSAP_FLUX", "SAP_FLUX"]:
        before, _ = followup_loader()(TIC, flux_column=flux)
        assert set(map(int, before.sector.unique())).isdisjoint(plan["original_sectors"])
        assert np.intersect1d(np.round(before.time, 8), np.round(original_times.time, 8)).size == 0
        after, models = weak(before, stars.loc[TIC])
        frames[flux] = dict(before_harmonics=before, after_harmonics=after)
        model_records[flux] = models
    rows = []
    for signal in plan["signals"]:
        period, epoch, duration = (
            signal[k] for k in ["period_days", "epoch_btjd", "duration_days"]
        )
        row = dict(**signal, views={})
        fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
        for i, (flux, stages) in enumerate(frames.items()):
            row["views"][flux] = {}
            for j, (stage, data) in enumerate(stages.items()):
                original = search.event_checks(data, period, epoch, duration)
                quadratic = continuum_train(
                    data, period, epoch, duration, degree=2, width_scale=1.0
                )
                divisor = round(period / 1.316)
                kernel = EventContrasts(data)
                classes = [
                    dict(
                        phase_class=k,
                        **kernel.measure(period, epoch + k * period / divisor, duration),
                    )
                    for k in range(divisor)
                ]
                assert np.isclose(
                    classes[0]["total_snr"], original["fixed_ephemeris_snr"], atol=1e-7
                )
                row["views"][flux][stage] = dict(
                    original=original,
                    quadratic=quadratic,
                    phase_divisor=divisor,
                    rotation_phase_classes=classes,
                    points=len(data),
                    sectors=sorted(map(int, data.sector.unique())),
                )
                folded_panel(
                    axes[i, j], data, signal, f"Fresh sectors: {flux}\n{stage.replace('_', ' ')}"
                )
        value = row["views"]["PDCSAP_FLUX"]["after_harmonics"]
        settings = plan["checks"]
        checks = {}
        for name, n, positive, snr in [
            (
                "original",
                value["original"]["n_observed_events"],
                value["original"]["n_positive_events"],
                value["original"]["fixed_ephemeris_snr"],
            ),
            (
                "quadratic",
                value["quadratic"]["events"],
                value["quadratic"]["positive_events"],
                value["quadratic"]["nominal_snr"],
            ),
        ]:
            checks[name] = dict(
                enough_events=n >= settings["minimum_measurable_events"],
                positive_fraction=positive / max(n, 1),
                snr=snr,
                passed=n >= settings["minimum_measurable_events"]
                and positive / max(n, 1) >= settings["minimum_positive_fraction"]
                and (snr or 0) >= settings["minimum_nominal_pdc_snr"],
            )
        row["recurrence_screen"] = dict(
            checks=checks, passed=all(c["passed"] for c in checks.values())
        )
        fig.suptitle(
            f"TIC {TIC}: fixed {period:.6f}-day {signal['role']} trial\nPreviously unexamined archived sectors; no timing adjustment",
            fontsize=14,
        )
        fig.savefig(OUT / f"{signal['method']}_fold.png", dpi=150)
        plt.close(fig)
        write(OUT / f"{signal['method']}.json", row)
        rows.append(
            {k: v for k, v in row.items() if k != "views"}
            | {
                "scores": {
                    flux: {
                        stage: dict(
                            original=v["original"]["fixed_ephemeris_snr"],
                            quadratic=v["quadratic"]["nominal_snr"],
                        )
                        for stage, v in stages.items()
                    }
                    for flux, stages in row["views"].items()
                }
            }
        )
        print(signal["method"], json.dumps(row["recurrence_screen"]), flush=True)
    write(
        OUT / "results.json",
        dict(
            completed_utc=datetime.now(timezone.utc).isoformat(),
            plan_sha256=sha(OUT / "plan.json"),
            manifest_sha256=sha(OUT / "download_manifest.json"),
            rows=rows,
            harmonic_models=model_records,
            original_and_fresh_sectors_disjoint=True,
            original_and_fresh_processed_timestamps_disjoint=True,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["prepare", "download", "analyze"])
    args = parser.parse_args()
    {"prepare": prepare, "download": download, "analyze": analyze}[args.operation]()
