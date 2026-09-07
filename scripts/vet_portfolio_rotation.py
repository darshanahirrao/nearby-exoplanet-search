"""Explore published rotation aliases of the two unmodified shortlist fits.

This does not change any search, threshold or experiment outcome. All phase
classes are examined and saved. Nominal scores are not false-alarm probabilities.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from longbaseline import sector_split
from multimode_cycle_experiment import weak
from repeated_events import EventContrasts
from search import event_checks, load_target

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/vetting/portfolio_rotation"
QUEUE = ROOT / "reports/experiments/portfolio/unmodified_review_queue.json"
TIC = 233738219
PUBLISHED_ROTATION = 1.316


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalogue_checks():
    sources = [
        (
            "TOI",
            "https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv",
            "TIC ID",
            ["TIC ID", "TOI", "Period (days)"],
        ),
        (
            "CTOI",
            "https://exofop.ipac.caltech.edu/tess/download_ctoi.php?sort=ctoi&output=csv",
            "TIC ID",
            ["TIC ID", "CTOI", "Period (days)"],
        ),
        (
            "NASA confirmed planets",
            "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?"
            + requests.compat.urlencode(
                {
                    "query": "select pl_name,hostname,tic_id,pl_orbper from pscomppars where tic_id='TIC 233738219'",
                    "format": "csv",
                }
            ),
            "tic_id",
            ["pl_name", "hostname", "tic_id", "pl_orbper"],
        ),
    ]
    records = []
    for name, url, id_column, columns in sources:
        record = dict(name=name, url=url, checked_utc=datetime.now(timezone.utc).isoformat())
        try:
            response = requests.get(url, timeout=(15, 45))
            response.raise_for_status()
            data = pd.read_csv(io.BytesIO(response.content))
            ids = pd.to_numeric(
                data[id_column].astype(str).str.replace("TIC ", "", regex=False),
                errors="coerce",
            )
            selected = data.loc[ids == TIC, columns]
            record.update(
                status="checked",
                response_sha256=hashlib.sha256(response.content).hexdigest(),
                response_bytes=len(response.content),
                catalogue_rows=len(data),
                exact_tic_matches=json.loads(selected.to_json(orient="records")),
            )
        except Exception as exc:
            record.update(status="error", error=repr(exc))
        records.append(record)
        print(name, record["status"], len(record.get("exact_tic_matches", [])), flush=True)
    return records


def event_panels(method, signal, parts):
    period, epoch, duration = (signal[k] for k in ["period_days", "epoch_btjd", "duration_days"])
    events = []
    for name, data in zip(["training", "holdout"], parts):
        checks = event_checks(data, period, epoch, duration)
        events.extend((name, data, event) for event in checks["event_snr"])
    columns = 4
    rows = int(np.ceil(len(events) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(13, rows * 2.1), squeeze=False)
    for ax, (name, data, event) in zip(axes.flat, events):
        time = (data.time.to_numpy() - event["center_btjd"]) * 24
        keep = abs(time) < 14.4
        x, y = time[keep], (data.flux.to_numpy()[keep] - 1) * 1000
        ax.plot(x, y, ".", ms=2, alpha=0.35, color="#397c94")
        edges = np.arange(-14.4, 14.401, 0.5)
        bins = np.digitize(x, edges)
        centers, medians = [], []
        for j in range(1, len(edges)):
            inside = bins == j
            centers.append((edges[j - 1] + edges[j]) / 2)
            medians.append(np.median(y[inside]) if inside.sum() >= 2 else np.nan)
        ax.plot(centers, medians, "-", lw=1, color="#a04b35")
        ax.axvspan(-duration * 12, duration * 12, color="#397c94", alpha=0.12)
        ax.axhline(0, color="0.6", lw=0.5)
        ax.set_title(
            f"{name}, BTJD {event['center_btjd']:.2f}\nnominal event SNR {event['snr']:.2f}",
            fontsize=8,
        )
        ax.set(xlim=(-14.4, 14.4), xlabel="Hours from supplied timing", ylabel="Flux [ppt]")
        ax.tick_params(labelsize=7)
        if len(y):
            lo, hi = np.percentile(y, [1, 99])
            pad = max((hi - lo) * 0.15, 0.3)
            ax.set_ylim(lo - pad, hi + pad)
    for ax in list(axes.flat)[len(events) :]:
        ax.set_visible(False)
    fig.suptitle(
        f"TIC {TIC}: {period:.6f} days, every observed event\nUninjected PDC after frozen harmonic processing; exploratory vetting"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / f"{method}_events.png", dpi=140)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    queue = json.loads(QUEUE.read_text())["trials"]
    star_path = ROOT / "data/catalogs/all_hz_targets.csv"
    star = pd.read_csv(star_path).set_index("TIC").loc[TIC]
    frames, models = {}, {}
    for flux in ["PDCSAP_FLUX", "SAP_FLUX"]:
        original, _ = load_target(TIC, flux_column=flux)
        cleaned, records = weak(original, star)
        frames[flux] = {
            "before_harmonics": sector_split(original),
            "after_harmonics": sector_split(cleaned),
        }
        models[flux] = records
        print(flux, "loaded", len(original), flush=True)
    rows = []
    for trial in queue:
        source = ROOT / trial["result_path"]
        assert sha(source) == trial["result_sha256"]
        signal = trial["signal"]
        period, epoch, duration = (
            signal[k] for k in ["period_days", "epoch_btjd", "duration_days"]
        )
        divisor = int(round(period / PUBLISHED_ROTATION))
        row = dict(
            method=trial["method"],
            period_days=period,
            epoch_btjd=epoch,
            duration_days=duration,
            divisor=divisor,
            tested_short_period_days=period / divisor,
            offset_from_published_mean_days=period / divisor - PUBLISHED_ROTATION,
            source=trial["result_path"],
            source_sha256=sha(source),
            views={},
        )
        fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
        for i, (flux, variants) in enumerate(frames.items()):
            row["views"][flux] = {}
            for j, (stage, parts) in enumerate(variants.items()):
                row["views"][flux][stage] = {}
                ax = axes[i, j]
                for name, data, color in zip(
                    ["training", "holdout"], parts, ["#397c94", "#a04b35"]
                ):
                    kernel = EventContrasts(data)
                    classes = [
                        dict(
                            phase_class=k,
                            **kernel.measure(period, epoch + k * period / divisor, duration),
                        )
                        for k in range(divisor)
                    ]
                    direct = event_checks(data, period, epoch, duration)
                    assert np.isclose(
                        classes[0]["total_snr"], direct["fixed_ephemeris_snr"], atol=1e-7
                    )
                    scores = np.array([c["total_snr"] for c in classes])
                    row["views"][flux][stage][name] = dict(
                        phase_classes=classes,
                        zero_class_event_checks=direct,
                        positive_other_classes=int(np.sum(scores[1:] > 0)),
                        other_classes_at_least_zero_score=int(np.sum(scores[1:] >= scores[0])),
                        median_other_class_snr=float(np.median(scores[1:])),
                        full_short_period=kernel.measure(period / divisor, epoch, duration),
                        points=len(data),
                        sectors=sorted(map(int, data.sector.unique())),
                    )
                    ax.plot(range(divisor), scores, ".-", color=color, label=name, ms=4, lw=1)
                    ax.scatter([0], [scores[0]], s=75, facecolors="none", edgecolors=color)
                ax.axhline(0, color="0.5", lw=0.7)
                ax.set(
                    title=f"{flux}: {stage.replace('_', ' ')}",
                    xlabel="Phase class (0 = supplied fit)",
                    ylabel="Nominal local-depth SNR",
                )
                ax.legend(fontsize=8)
        fig.suptitle(
            f"TIC {TIC}: {period:.6f}-day fit divided into {divisor} phase classes\nStep = {period / divisor:.6f} days; exploratory rotation check"
        )
        fig.savefig(OUT / f"{trial['method']}_classes.png", dpi=150)
        plt.close(fig)
        event_panels(trial["method"], signal, frames["PDCSAP_FLUX"]["after_harmonics"])
        (OUT / f"{trial['method']}.json").write_text(json.dumps(row, indent=2) + "\n")
        rows.append(row)
        print(trial["method"], "phase classes complete", flush=True)
    result = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        script_sha256=sha(Path(__file__)),
        review_queue_sha256=sha(QUEUE),
        star_catalogue_sha256=sha(star_path),
        helpers_sha256={
            name: sha(ROOT / "scripts" / name)
            for name in [
                "search.py",
                "physics.py",
                "longbaseline.py",
                "variability.py",
                "cycle_excluded.py",
                "multimode_cycle_experiment.py",
                "repeated_events.py",
            ]
        },
        telescope_inputs_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in sorted((ROOT / "data/lightcurves" / str(TIC)).glob("*_lc.fits"))
        },
        literature=dict(
            url="https://arxiv.org/pdf/2207.03794",
            table=1,
            rotation_days=PUBLISHED_ROTATION,
            reported_scatter_days=0.010,
        ),
        harmonic_models=models,
        catalogue_checks=catalogue_checks(),
        trials=[{k: v for k, v in row.items() if k != "views"} for row in rows],
        scope="Exploratory check of selected unmodified fits, not independent validation. All phase classes are disclosed. Period divisors come from the published rotation period. Before-harmonic data still use the original 1.5-day median trend. SAP and PDC share pixels. Local windows and correlated stellar noise prevent treating nominal SNR as a calibrated significance. Exact-TIC catalogue checks do not prove novelty or exclude off-target sources.",
    )
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Diagnostic completed", flush=True)


if __name__ == "__main__":
    main()
