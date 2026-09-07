"""Fixed-ephemeris diagnostics for TIC 142086813; no new search or gate changes."""

from datetime import datetime, timezone
import inspect
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import coverage_pilot as pilot
from local_baseline import continuum_train
from multimode_cycle_experiment import weak
import search
from vet import folded_panel
import vet_portfolio_rotation as earlier

ROOT = pilot.ROOT
OUT = ROOT / "reports/vetting/coverage_142086813"
TIC = 142086813


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    folder = ROOT / "results" / f"{TIC}_coverage_pilot"
    result = json.loads((folder / "result.json").read_text())
    signal = result["signals"][1]
    assert not signal["screening_flags"]
    execution_hash = pilot.sha(ROOT / "reports/coverage_continuation/execution_plan.json")
    receipt = pilot.adapted_functions()["checked_cache"](TIC, execution_hash)
    assert receipt is not None
    period, epoch, duration = (signal[k] for k in ["period_days", "epoch_btjd", "duration_days"])
    sources = {}
    views = {}
    for tic, prefix in [(TIC, "target"), (142086812, "companion")]:
        for name, filename in [
            ("PDC_before", "unfiltered_lightcurve.csv.gz"),
            ("PDC_after", "lightcurve.csv.gz"),
        ]:
            path = ROOT / "results" / f"{tic}_coverage_pilot" / filename
            sources[str(path.relative_to(ROOT))] = pilot.sha(path)
            views[prefix + "_" + name] = pd.read_csv(path)
    source = inspect.getsource(search.load_target)
    old = 'ROOT / "data/lightcurves" / str(tic)'
    assert source.count(old) == 1
    namespace = dict(vars(search))
    exec(
        compile(
            source.replace(old, 'ROOT / "data/coverage_lightcurves" / str(tic)'),
            "<coverage-SAP-loader>",
            "exec",
        ),
        namespace,
    )
    sap_old, _ = search.load_target(TIC, flux_column="SAP_FLUX")
    sap_added, _ = namespace["load_target"](TIC, flux_column="SAP_FLUX")
    assert set(sap_old.sector).isdisjoint(sap_added.sector)
    sap = pd.concat([sap_old, sap_added], ignore_index=True).sort_values("time")
    assert not sap.time.duplicated().any()
    views["target_SAP_before"] = sap
    views["target_SAP_after"], _ = weak(sap, pd.Series(result["star"]))
    for directory in [ROOT / "data/lightcurves" / str(TIC), pilot.EXTRA / str(TIC)]:
        for path in directory.glob("*_lc.fits"):
            sources[str(path.relative_to(ROOT))] = pilot.sha(path)
    for name in [
        "vet_coverage_trial.py",
        "local_baseline.py",
        "search.py",
        "vet.py",
        "vet_portfolio_rotation.py",
        "multimode_cycle_experiment.py",
        "coverage_pilot.py",
    ]:
        sources["scripts/" + name] = pilot.sha(ROOT / "scripts" / name)

    measurements = {}
    fig, axes = plt.subplots(len(views), 2, figsize=(12, 3 * len(views)), constrained_layout=True)
    event_rows = []
    for row, (name, frame) in enumerate(views.items()):
        measurements[name] = {}
        for col, part in enumerate(["training", "holdout"]):
            data = frame.loc[frame.sector.isin(result[part + "_sectors"])]
            original = search.event_checks(data, period, epoch, duration)
            search_replay = None
            if name == "target_PDC_after":
                saved = signal["discovery" if part == "training" else "holdout"]
                replay = data
                if part == "training":
                    first = result["signals"][0]
                    phase = (
                        data.time.to_numpy() - first["epoch_btjd"] + first["period_days"] / 2
                    ) % first["period_days"] - first["period_days"] / 2
                    replay = data.loc[abs(phase) > first["duration_days"] * 1.25]
                search_replay = search.event_checks(replay, period, epoch, duration)
                assert np.isclose(
                    search_replay["fixed_ephemeris_snr"], saved["fixed_ephemeris_snr"], atol=1e-7
                )
                event_rows.extend((part, data, event) for event in original["event_snr"])
            baselines = [
                dict(
                    degree=degree,
                    width_scale=width,
                    **continuum_train(data, period, epoch, duration, degree, width),
                )
                for degree in [0, 1, 2]
                for width in [0.75, 1.0, 1.25]
            ]
            events = original["event_snr"]
            leave_one_out = []
            for event in events:
                kept = [e for e in events if e["cycle"] != event["cycle"]]
                errors = np.array([e["error"] for e in kept])
                depths = np.array([e["depth"] for e in kept])
                value = (
                    float(np.sum(depths / errors**2) / np.sqrt(np.sum(1 / errors**2)))
                    if kept
                    else None
                )
                leave_one_out.append(dict(removed_cycle=event["cycle"], nominal_snr=value))
            measurements[name][part] = dict(
                original=original,
                search_replay=search_replay,
                baselines=baselines,
                leave_one_out=leave_one_out,
            )
            folded_panel(axes[row, col], data, signal, name + ": " + part)
    fig.suptitle(f"TIC {TIC}, fixed {period:.8f}-day trial; exploratory diagnostics")
    fig.savefig(OUT / "folds.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(
        int(np.ceil(len(event_rows) / 4)),
        4,
        figsize=(14, 10),
        squeeze=False,
        constrained_layout=True,
    )
    for ax, (part, frame, event) in zip(axes.flat, event_rows):
        time = (frame.time.to_numpy() - event["center_btjd"]) * 24
        keep = abs(time) < max(4 * duration, 0.3) * 24
        ax.plot(time[keep], (frame.flux.to_numpy()[keep] - 1) * 1000, ".-", ms=2, lw=0.4)
        ax.axvspan(-duration * 12, duration * 12, alpha=0.15)
        ax.set(
            title=f"{part}, cycle {event['cycle']}\nBTJD {event['center_btjd']:.3f}; SNR {event['snr']:.2f}",
            xlabel="Hours from fixed timing",
            ylabel="Relative flux [ppt]",
        )
    for ax in list(axes.flat)[len(event_rows) :]:
        ax.set_visible(False)
    fig.suptitle("Every measurable event: processed target PDC, full local window")
    fig.savefig(OUT / "events.png", dpi=130)
    plt.close(fig)

    earlier.TIC = TIC
    catalogue_source = inspect.getsource(earlier.catalogue_checks)
    assert catalogue_source.count("233738219") == 1
    ns = dict(vars(earlier))
    exec(
        compile(
            catalogue_source.replace("233738219", str(TIC)), "<coverage-catalogue-check>", "exec"
        ),
        ns,
    )
    record = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        tic=TIC,
        signal_index=2,
        original_receipt=receipt,
        source_sha256=sources,
        frozen_signal=signal,
        measurements=measurements,
        catalogue_checks=ns["catalogue_checks"](),
        scope="Exploratory diagnostics at the unchanged supplied training ephemeris. The first-fit training mask is replayed to verify the saved second-fit search score; the subsequent diagnostics restore all samples. All nine local baseline choices, every observed event and every leave-one-event-out score are reported. PDC/SAP share pixels; the companion extraction can share target flux. Nominal errors omit time correlation and do not establish calibrated significance, independent confirmation, unique source identity or a discovery. No search or screening gate changed.",
    )
    pilot.save(OUT / "diagnostics.json", record)
    compact = {
        name: {
            part: dict(
                original_snr=d["original"]["fixed_ephemeris_snr"],
                quadratic_scores=[x["nominal_snr"] for x in d["baselines"] if x["degree"] == 2],
                leave_one_out=d["leave_one_out"],
            )
            for part, d in parts.items()
        }
        for name, parts in measurements.items()
    }
    pilot.save(OUT / "summary.json", compact)
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
