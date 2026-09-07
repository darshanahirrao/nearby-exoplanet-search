"""Selected-case development diagnostic; known injection truth is used for scoring only."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from longbaseline import sector_split
from multimode_cycle_experiment import weak
from physical_duration import PhysicalDurationBLS
from physics import stellar_hz
from realistic_injections import make_loader
from repeated_events import EventContrasts, distinct_peaks
from search import bin_series

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / "reports/experiments/period_rank_diagnostic"
    folder.mkdir(exist_ok=True)
    source = ROOT / "reports/experiments/pipeline_confirmation"
    previous = json.loads((source / "plan.json").read_text())
    # Two clear missed-period examples and an already recovered positive control.
    ids = ["233738219_orbit2_radius1", "229614158_orbit0_radius1", "328799321_orbit1_radius1"]
    cases = [c for c in previous["cases"] if c["method"] == "coarse_only" and c["paired_id"] in ids]
    files = [
        str(Path(__file__).relative_to(ROOT)),
        "scripts/repeated_events.py",
        "docs/DIAGNOSTIC_PERIOD_RANKING.md",
    ]
    hashes = {
        **previous["source_sha256"],
        **previous["catalogue_sha256"],
        **previous["telescope_inputs_sha256"],
    }
    for name, digest in hashes.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Confirmation input changed: {name}")
    hashes.update({name: sha(ROOT / name) for name in files})
    spec = dict(source_sha256=hashes, cases=cases, maximum_distinct_seeds=4096, scope=__doc__)
    path = folder / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != v for k, v in spec.items()):
            raise ValueError("Preserve the diagnostic protocol")
    else:
        path.write_text(
            json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec), indent=2)
            + "\n"
        )
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    rows = []
    for case in cases:
        star = stars.loc[case["tic"]]
        data, _ = make_loader(case, star)(
            case["tic"],
            inject=dict(
                period=case["period_days"],
                epoch=case["epoch_btjd"],
                depth=case["depth"],
                duration=case["duration_days"],
            ),
        )
        data, _ = weak(data, star)
        training, _ = sector_split(data)
        hz = stellar_hz(star)
        coarse = []
        for sector, part in training.groupby("sector"):
            t, y, e = bin_series(
                part.time.to_numpy(), part.flux.to_numpy(), part.err.to_numpy(), step=30 / 1440
            )
            coarse.append(pd.DataFrame(dict(time=t, flux=y, err=e)))
        coarse = pd.concat(coarse).sort_values("time")
        baseline = float(np.ptp(training.time))
        low, high = (
            max(1, 0.85 * hz["inner_period"]),
            min(100, 1.15 * hz["outer_period"], 0.48 * baseline),
        )
        count = max(3000, int(np.ceil(np.log(high / low) * 3 * baseline / 0.04)) + 1)
        periods = np.geomspace(low, high, count)
        power = PhysicalDurationBLS(
            coarse.time.to_numpy(), coarse.flux.to_numpy(), coarse.err.to_numpy(), star=star
        ).power(periods, [0.04], objective="likelihood", oversample=5)
        candidates = distinct_peaks(power, baseline, hz["inner_period"], hz["outer_period"])
        contrast = EventContrasts(training)
        seeds = []
        for rank, k in enumerate(candidates, 1):
            p, t0, duration = (
                float(power[name][k]) for name in ["period", "transit_time", "duration"]
            )
            measure = contrast.measure(p, t0, duration)
            drift = []
            for t in [training.time.min(), training.time.max()]:
                center = t0 + round((t - t0) / p) * p
                drift.append(
                    float(
                        abs(
                            (center - case["epoch_btjd"] + case["period_days"] / 2)
                            % case["period_days"]
                            - case["period_days"] / 2
                        )
                    )
                )
            seeds.append(
                dict(
                    global_rank=rank,
                    period_days=p,
                    epoch_btjd=t0,
                    duration_days=duration,
                    **measure,
                    true_timing_match=bool(
                        abs(p / case["period_days"] - 1) < 0.01
                        and max(drift) < 0.75 * case["duration_days"]
                    ),
                )
            )
        matches = [r for r in seeds if r["true_timing_match"]]
        ranking = {}
        for field in ["total_snr", "leave_one_out_snr"]:
            order = sorted(seeds, key=lambda r: -(r[field] if r[field] is not None else -np.inf))
            ranking[field] = dict(
                first_matching_rank=next(
                    (i for i, r in enumerate(order, 1) if r["true_timing_match"]), None
                ),
                best=order[0],
            )
        report = dict(
            id=case["id"],
            seeds=len(seeds),
            true_period=case["period_days"],
            first_global_match=matches[0] if matches else None,
            ranking=ranking,
            supplied_truth=contrast.measure(
                case["period_days"], case["epoch_btjd"], case["duration_days"]
            ),
            scope=__doc__,
        )
        (folder / (case["paired_id"] + ".json")).write_text(
            json.dumps(dict(report, all_seeds=seeds), indent=2, allow_nan=False) + "\n"
        )
        rows.append(report)
        print(json.dumps(report), flush=True)
    (folder / "results.json").write_text(
        json.dumps(dict(rows=rows, completed_utc=datetime.now(timezone.utc).isoformat()), indent=2)
        + "\n"
    )


if __name__ == "__main__":
    main()
