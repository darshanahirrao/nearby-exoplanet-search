"""Post-result diagnostics for two missed synthetic signals, not blind recovery."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from longbaseline import sector_split
from parallel_bls import ParallelBoxLeastSquares
from physics import stellar_hz, central_duration
from search import bin_series, event_checks, load_target
from variability import clean_variability

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "reports/experiments/cycle_excluded/plan.json"
    ids = {
        "production_harmonic__352617553_orbit0_radius0.6",
        "production_harmonic__352617553_orbit1_radius0.8",
    }
    cases = [c for c in json.loads(source.read_text())["cases"] if c["id"] in ids]
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    rows = []
    for case in cases:
        star = stars.loc[case["tic"]]
        df, _ = load_target(
            case["tic"],
            inject=dict(
                period=case["period_days"],
                epoch=case["epoch_btjd"],
                depth=case["depth"],
                duration=case["duration_days"],
            ),
        )
        for passes in [1, 3]:
            clean = df.copy()
            records = []
            for _ in range(passes):
                clean, record = clean_variability(clean, star)
                records.extend(record)
            training, _ = sector_split(clean)
            parts = []
            for sector, part in training.groupby("sector"):
                t, y, e = bin_series(
                    part.time.to_numpy(), part.flux.to_numpy(), part.err.to_numpy(), step=30 / 1440
                )
                parts.append(pd.DataFrame(dict(time=t, flux=y, err=e, sector=sector)))
            coarse = pd.concat(parts).sort_values("time")
            hz = stellar_hz(star)
            low = max(1, 0.85 * hz["inner_period"])
            high = min(100, 1.15 * hz["outer_period"], 0.48 * np.ptp(training.time))
            count = max(
                3000, int(np.ceil(np.log(high / low) * 3 * np.ptp(training.time) / 0.04)) + 1
            )
            periods = np.geomspace(low, high, count)
            model = ParallelBoxLeastSquares(coarse.time, coarse.flux, coarse.err)
            variants = {}
            for name, durations in [
                ("production_coarse", [0.04, 0.06, 0.09, 0.13, 0.18, 0.25]),
                ("short_durations", [0.02, 0.03, 0.04, 0.06, 0.09]),
            ]:
                power = model.power(periods, durations, objective="likelihood", oversample=5)
                close = abs(periods / case["period_days"] - 1) < case["duration_days"] / np.ptp(
                    training.time
                )
                near = np.flatnonzero(close)
                best = near[np.argmax(power.power[near])]
                top = np.argsort(power.power)[::-1]
                unique = []
                for i in top:
                    if all(
                        abs(periods[i] / s["period_days"] - 1) > 3 * 0.09 / np.ptp(training.time)
                        for s in unique
                    ):
                        unique.append(
                            dict(
                                period_days=float(periods[i]),
                                duration_days=float(power.duration[i]),
                                snr=float(power.depth_snr[i]),
                                epoch_btjd=float(power.transit_time[i]),
                                circular_duration_days=float(central_duration(periods[i], star)),
                            )
                        )
                    if len(unique) == 8:
                        break
                variants[name] = dict(
                    top_distinct_peaks=unique,
                    injected_period_neighborhood=dict(
                        period_days=float(periods[best]),
                        snr=float(power.depth_snr[best]),
                        duration_days=float(power.duration[best]),
                        epoch_btjd=float(power.transit_time[best]),
                        grid_points_above=int(np.sum(power.power > power.power[best])),
                    ),
                )
            row = dict(
                case=case["id"],
                period_days=case["period_days"],
                duration_days=case["duration_days"],
                cleaning_passes=passes,
                models=records,
                forced_training=event_checks(
                    training, case["period_days"], case["epoch_btjd"], case["duration_days"]
                ),
                forced_coarse=event_checks(
                    coarse, case["period_days"], case["epoch_btjd"], case["duration_days"]
                ),
                variants=variants,
            )
            rows.append(row)
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in row.items()
                        if k not in ["models", "forced_training", "forced_coarse"]
                    }
                ),
                flush=True,
            )
    out = ROOT / "reports/experiments/search_bottleneck"
    out.mkdir(parents=True, exist_ok=True)
    (out / "diagnostic.json").write_text(
        json.dumps(
            dict(
                scope="Post-result diagnostic on two selected known injections; no blind recovery or calibrated significance.",
                created_utc=datetime.now(timezone.utc).isoformat(),
                source_plan_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                rows=rows,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
