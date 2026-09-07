"""Fixed local-continuum sensitivity checks with real and injected controls."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from local_baseline import continuum_train
from longbaseline import sector_split
from multimode_cycle_experiment import weak
from realistic_injections import make_loader
from search import event_checks, load_target

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/vetting/local_baseline_sensitivity"
DEGREES = [0, 1, 2]
WIDTHS = [0.75, 1.0, 1.25]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def setup():
    queue_path = "reports/experiments/portfolio/unmodified_review_queue.json"
    control_path = "reports/calibration/revised_pipeline/coarse_only/result.json"
    control_data = "results/150428135_calibration_v2/lightcurve.csv.gz"
    injection_path = (
        "results/portfolio_development/leave_one_out__233738219_orbit2_radius1/result.json"
    )
    injection_fit = (
        "results/portfolio_development/leave_one_out__233738219_orbit2_radius1/frozen_search.json"
    )
    cases = []
    inputs = {
        queue_path,
        control_path,
        control_data,
        injection_path,
        injection_fit,
        "data/catalogs/all_hz_targets.csv",
    }
    for trial in read(queue_path)["trials"]:
        inputs.add(trial["result_path"])
        assert sha(ROOT / trial["result_path"]) == trial["result_sha256"]
        for flux in ["PDCSAP_FLUX", "SAP_FLUX"]:
            cases.append(
                dict(
                    id=trial["method"] + "_" + flux,
                    tic=trial["tic"],
                    kind="unmodified_trial",
                    flux=flux,
                    signal=trial["signal"],
                )
            )
    control = read(control_path)
    assert sha(ROOT / control_data) == control["source_sha256"]
    signal = min(control["signals"], key=lambda s: abs(s["period_days"] - 37.424))
    assert abs(signal["period_days"] - 37.424) < 0.01
    cases.append(
        dict(
            id="known_TOI700d_PDCSAP",
            tic=150428135,
            kind="known_planet_control",
            flux="PDCSAP_FLUX",
            signal=signal,
        )
    )
    injection = read(injection_path)
    signal = min(
        read(injection_fit)["signals"],
        key=lambda s: abs(s["period_days"] - injection["period_days"]),
    )
    assert abs(signal["period_days"] / injection["period_days"] - 1) < 0.001
    cases.append(
        dict(
            id="injected_233738219_orbit2_radius1",
            tic=233738219,
            kind="physical_injection_control",
            flux="PDCSAP_FLUX",
            signal=signal,
            injection=injection,
        )
    )
    for p in (ROOT / "data/lightcurves/233738219").glob("*_lc.fits"):
        inputs.add(str(p.relative_to(ROOT)))
    helpers = [
        "local_baseline.py",
        "vet_local_baselines.py",
        "search.py",
        "physics.py",
        "variability.py",
        "cycle_excluded.py",
        "multimode_cycle_experiment.py",
        "realistic_injections.py",
        "longbaseline.py",
    ]
    spec = dict(
        degrees=DEGREES,
        baseline_width_scales=WIDTHS,
        source_sha256={p: sha(ROOT / "scripts" / p) for p in helpers},
        input_sha256={p: sha(ROOT / p) for p in sorted(inputs)},
        cases=cases,
        scope="Exploratory vetting on already exposed data. All nine baseline choices reported. Protected window is +/- one supplied duration; baseline outer radius is max(4*duration,0.3 days) times the stated scale. At least four baseline samples on each side and three event samples required. Supplied training fits fixed; no period search or gate changes. Neither these controls nor nominal polynomial errors establish general transit preservation or a calibrated false-alarm probability.",
    )
    plan_path = OUT / "plan.json"
    if plan_path.exists():
        prior = json.loads(plan_path.read_text())
        if any(prior[k] != v for k, v in spec.items()):
            raise ValueError("Preserve the existing diagnostic; inputs or specification changed")
    else:
        plan_path.write_text(
            json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec), indent=2)
            + "\n"
        )
    return cases, control, control_data


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases, control, control_data = setup()
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    frames = {}
    for flux in ["PDCSAP_FLUX", "SAP_FLUX"]:
        original, _ = load_target(233738219, flux_column=flux)
        cleaned, _ = weak(original, stars.loc[233738219])
        frames[("unmodified_trial", flux)] = sector_split(cleaned)
    original = pd.read_csv(ROOT / control_data)
    cleaned, _ = weak(original, pd.Series(control["star"]))
    frames[("known_planet_control", "PDCSAP_FLUX")] = sector_split(cleaned)
    injection = cases[-1]["injection"]
    original, _ = make_loader(injection, stars.loc[233738219])(
        233738219,
        inject=dict(
            period=injection["period_days"],
            epoch=injection["epoch_btjd"],
            depth=injection["depth"],
            duration=injection["duration_days"],
        ),
    )
    cleaned, _ = weak(original, stars.loc[233738219])
    frames[("physical_injection_control", "PDCSAP_FLUX")] = sector_split(cleaned)
    rows, direct_checks = [], 0
    fig, axes = plt.subplots(3, 2, figsize=(14, 11), constrained_layout=True)
    labels = [
        f"{['Flat', 'Linear', 'Quadratic'][degree]}\n{width:g}× width"
        for degree in DEGREES
        for width in WIDTHS
    ]
    for ax, case in zip(axes.flat, cases):
        signal = case["signal"]
        period, epoch, duration = (
            signal[k] for k in ["period_days", "epoch_btjd", "duration_days"]
        )
        row = dict(
            id=case["id"],
            tic=case["tic"],
            kind=case["kind"],
            period_days=period,
            epoch_btjd=epoch,
            duration_days=duration,
            parts={},
        )
        for part, frame, color in zip(
            ["training", "holdout"], frames[(case["kind"], case["flux"])], ["#397c94", "#a04b35"]
        ):
            original = event_checks(frame, period, epoch, duration)
            if case["flux"] == "PDCSAP_FLUX":
                saved = signal.get("discovery" if part == "training" else "holdout")
                if saved is not None:
                    assert np.isclose(
                        original["fixed_ephemeris_snr"], saved["fixed_ephemeris_snr"], atol=1e-7
                    )
                    direct_checks += 1
            measurements = []
            for degree in DEGREES:
                for width in WIDTHS:
                    measured = continuum_train(frame, period, epoch, duration, degree, width)
                    measured.update(degree=degree, width_scale=width)
                    if degree == 0 and width == 1:
                        prior_events = {e["cycle"]: e for e in original["event_snr"]}
                        for event in measured["event_measurements"]:
                            if event["status"] == "measured":
                                prior = prior_events[event["cycle"]]
                                assert np.isclose(event["depth"], prior["depth"], atol=1e-12)
                                assert np.isclose(event["error"], prior["error"], atol=1e-12)
                                direct_checks += 2
                    measurements.append(measured)
            row["parts"][part] = dict(
                original=original,
                baselines=measurements,
                points=len(frame),
                sectors=sorted(map(int, frame.sector.unique())),
            )
            ax.plot(
                range(len(labels)),
                [m["nominal_snr"] for m in measurements],
                ".-",
                color=color,
                label=part,
            )
            ax.axhline(original["fixed_ephemeris_snr"], color=color, lw=0.7, ls="--", alpha=0.6)
        ax.axhline(0, color="0.5", lw=0.7)
        ax.set_xticks(range(len(labels)), labels, fontsize=7, rotation=45, ha="right")
        ax.set(title=f"{case['id']}\n{period:.6f} days", ylabel="Nominal event-depth SNR")
        ax.legend(fontsize=8)
        (OUT / (case["id"] + ".json")).write_text(json.dumps(row, indent=2) + "\n")
        compact = {k: v for k, v in row.items() if k != "parts"}
        compact["parts"] = {
            name: dict(
                original_snr=p["original"]["fixed_ephemeris_snr"],
                original_events=p["original"]["n_observed_events"],
                baselines=[
                    {k: v for k, v in m.items() if k != "event_measurements"}
                    for m in p["baselines"]
                ],
            )
            for name, p in row["parts"].items()
        }
        rows.append(compact)
        print(case["id"], "complete", flush=True)
    fig.suptitle(
        "Local-baseline sensitivity: two unmodified fits and two controls\nAll choices disclosed; dashed lines are original scores; nominal statistics only",
        fontsize=14,
    )
    fig.savefig(OUT / "comparison.png", dpi=150)
    plt.close(fig)
    summary = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(OUT / "plan.json"),
        direct_checks=direct_checks,
        rows=rows,
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("Complete; direct checks", direct_checks, flush=True)


if __name__ == "__main__":
    main()
