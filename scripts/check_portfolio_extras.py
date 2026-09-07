"""Check two unmatched smoke-test fits in the original, uninjected observations."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from longbaseline import sector_split
from multimode_cycle_experiment import weak
from search import event_checks, load_target
from vet import folded_panel

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "reports/vetting/portfolio_extra_fits"
    folder.mkdir(parents=True, exist_ok=True)
    tic = 233738219
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[tic]
    sources = []
    for method, period in [
        ("local_total", 35.394137501476735),
        ("leave_one_out", 26.316459215610013),
    ]:
        path = (
            ROOT
            / "results/portfolio_development"
            / (method + "__233738219_orbit2_radius1")
            / "frozen_search.json"
        )
        data = json.loads(path.read_text())
        signal = next(s for s in data["signals"] if abs(s["period_days"] - period) < 1e-10)
        sources.append(
            dict(
                method=method,
                source=str(path.relative_to(ROOT)),
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                signal=signal,
            )
        )
    # The ephemerides are supplied by the development fits; do not search again.
    frames = {}
    for flux in ["PDCSAP_FLUX", "SAP_FLUX"]:
        original, _ = load_target(tic, flux_column=flux)
        cleaned, _ = weak(original, star)
        frames[flux] = sector_split(cleaned)
    rows = []
    for source in sources:
        signal = source["signal"]
        period = signal["period_days"]
        row = dict(
            tic=tic,
            method=source["method"],
            source=source["source"],
            source_sha256=source["source_sha256"],
            period_days=period,
            epoch_btjd=signal["epoch_btjd"],
            duration_days=signal["duration_days"],
            checks={},
            scope="Fixed timing from an injected development fit, checked on original uninjected data. Exploratory vetting, not blind recovery or planet validation. SAP and PDC share pixels.",
        )
        fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
        for i, (flux, parts) in enumerate(frames.items()):
            row["checks"][flux] = {}
            for j, (name, data) in enumerate(zip(["training", "holdout"], parts)):
                row["checks"][flux][name] = event_checks(
                    data, period, signal["epoch_btjd"], signal["duration_days"]
                )
                folded_panel(axes[i, j], data, signal, f"{flux}: {name}; no injected transit")
        fig.suptitle(f"TIC {tic} · supplied {period:.6f}-day fit · diagnostic only", fontsize=14)
        fig.savefig(folder / f"{source['method']}.png", dpi=150)
        plt.close(fig)
        (folder / f"{source['method']}.json").write_text(json.dumps(row, indent=2) + "\n")
        rows.append(
            {k: v for k, v in row.items() if k != "checks"}
            | {
                "snr": {
                    flux: {name: v["fixed_ephemeris_snr"] for name, v in checks.items()}
                    for flux, checks in row["checks"].items()
                }
            }
        )
    result = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        helper_sha256={
            name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
            for name in [
                "search.py",
                "physics.py",
                "variability.py",
                "cycle_excluded.py",
                "multimode_cycle_experiment.py",
                "longbaseline.py",
                "vet.py",
            ]
        },
        telescope_inputs_sha256={
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "data/lightcurves" / str(tic)).glob("*_lc.fits"))
        },
        rows=rows,
    )
    (folder / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
