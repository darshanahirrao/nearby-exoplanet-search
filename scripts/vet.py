"""Reproducible short-period variability checks for preliminary BLS signals."""

from datetime import datetime, timezone
import argparse, json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.timeseries import LombScargle
from scipy.optimize import minimize_scalar
from search import ROOT, split_campaigns, load_target, event_checks


def folded_panel(ax, df, signal, title):
    period = signal["period_days"]
    epoch = signal["epoch_btjd"]
    phase = (df.time.to_numpy() - epoch + period / 2) % period - period / 2
    flux = (df.flux.to_numpy() - 1) * 1000
    select = abs(phase) < 0.6
    ax.plot(phase[select] * 24, flux[select], ".", ms=1, alpha=0.15, color="#347299")
    edges = np.arange(-0.6, 0.605, 0.007)
    bins = np.digitize(phase, edges)
    x = []
    y = []
    for k in range(1, len(edges)):
        keep = bins == k
        x.append((edges[k - 1] + edges[k]) * 12)
        y.append(float(np.median(flux[keep])) if keep.sum() >= 3 else np.nan)
    ax.plot(x, y, ".-", ms=3, lw=0.8, color="#ad3b35")
    ax.axvspan(
        -signal["duration_days"] * 12, signal["duration_days"] * 12, alpha=0.12, color="#347299"
    )
    ax.set(title=title, xlabel="Time from fixed ephemeris [hours]", ylabel="Relative flux [ppt]")
    if select.any():
        lo, hi = np.percentile(flux[select], [0.2, 99.8])
        pad = max(1, (hi - lo) * 0.1)
        ax.set_ylim(lo - pad, hi + pad)


def vet(tic, iteration, refined=False, variant="base"):
    original = ROOT / "results" / str(tic)
    if variant == "variability":
        folder = original.with_name(original.name + "_variability")
        refined = True
    else:
        folder = original.with_name(original.name + "_refined") if refined else original
    r = json.loads((folder / "result.json").read_text())
    s = r["signals"][iteration - 1]
    df = pd.read_csv((folder if variant == "variability" else original) / "lightcurve.csv.gz")
    if refined:
        from refine import three_way_split

        dis, _, val, _ = three_way_split(df)
    else:
        dis, val, _ = split_campaigns(df)
    ls = LombScargle(dis.time, dis.flux, dis.err)
    frequency, power = ls.autopower(
        minimum_frequency=0.5, maximum_frequency=25, samples_per_peak=10
    )
    index = int(np.argmax(power))
    freq = frequency[index]
    step = frequency[1] - frequency[0]
    best_frequency = minimize_scalar(
        lambda f: -ls.power(f),
        bounds=(max(0.5, freq - step), min(25, freq + step)),
        method="bounded",
        options={"xatol": 1e-11},
    )
    freq = float(best_frequency.x)
    cycles = float(s["period_days"] * freq)
    multiple = int(round(cycles))
    residual_checks = {}
    for name, data in [("discovery", dis), ("holdout", val)]:
        if len(data) < 30:
            continue
        fit = LombScargle(data.time, data.flux, data.err, nterms=3).model(data.time, freq)
        corrected = data.copy()
        corrected["flux"] = data.flux - fit + 1
        residual_checks[name] = {
            "before": event_checks(data, s["period_days"], s["epoch_btjd"], s["duration_days"]),
            "after_fitting_short_variation": event_checks(
                corrected, s["period_days"], s["epoch_btjd"], s["duration_days"]
            ),
        }
    alignment = abs(s["period_days"] - multiple / freq)
    # Heuristic flag only; inspect folded and individual observations before disposition.
    alias = bool(
        multiple >= 3 and float(-best_frequency.fun) > 0.05 and alignment < s["duration_days"] / 2
    )
    evidence = {
        "tic": tic,
        "input_variant": variant,
        "signal_iteration": iteration,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "short_period_days": 1 / freq,
        "ls_fractional_power": float(-best_frequency.fun),
        "candidate_period_days": s["period_days"],
        "period_ratio": cycles,
        "nearest_integer_multiple": multiple,
        "alignment_error_days": float(alignment),
        "short_period_alias_suspected": alias,
        "residual_checks": residual_checks,
        "limitations": "Exploratory variability check, not a calibrated false-positive probability. SAP and PDC share pixels. Holdout variation amplitude/phase is fitted here, so residual checks are diagnostic, not untouched holdout evidence.",
    }
    out = folder / f"vet_signal_{iteration}"
    out.mkdir(exist_ok=True)
    (out / "variability.json").write_text(json.dumps(evidence, indent=2))
    sap, _ = load_target(tic, flux_column="SAP_FLUX")
    if variant == "variability":
        from variability import clean_variability

        sap, _ = clean_variability(sap, pd.Series(r["star"]))
    if refined:
        ds, _, vs, _ = three_way_split(sap)
    else:
        ds, vs, _ = split_campaigns(sap)
    rows = 3 if variant == "variability" else 2
    fig, axes = plt.subplots(rows, 2, figsize=(12, 3.5 * rows), constrained_layout=True)
    suffix = " after periodic model" if variant == "variability" else ""
    for ax, data, title in [
        (axes[0, 0], dis, "Discovery: PDC"),
        (axes[0, 1], val, "Held-back observations: PDC"),
        (axes[1, 0], ds, "Discovery: SAP"),
        (axes[1, 1], vs, "Held-back observations: SAP"),
    ]:
        folded_panel(ax, data, s, title + suffix)
    if variant == "variability":
        before = pd.read_csv(original / "lightcurve.csv.gz")
        db, _, vb, _ = three_way_split(before)
        folded_panel(axes[2, 0], db, s, "Discovery: PDC before periodic model")
        folded_panel(axes[2, 1], vb, s, "Held-back: PDC before periodic model")
    fig.suptitle(
        f"TIC {tic} | trial period {s['period_days']:.6f} days\nPreliminary diagnostics; no planet claim"
    )
    fig.savefig(out / "phase_diagnostics.png", dpi=160)
    plt.close(fig)
    print(
        tic,
        "signal",
        iteration,
        "short_period_hours",
        round(24 / freq, 5),
        "period_ratio",
        round(cycles, 5),
        "alias_suspected",
        alias,
        flush=True,
    )
    return evidence


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tic", required=True, type=int)
    p.add_argument("--signal", default=1, type=int)
    p.add_argument("--refined", action="store_true")
    p.add_argument("--variant", choices=["base", "variability"], default="base")
    a = p.parse_args()
    vet(a.tic, a.signal, a.refined, a.variant)


if __name__ == "__main__":
    main()
