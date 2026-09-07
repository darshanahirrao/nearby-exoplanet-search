"""Rescore already fitted training candidates; this is exposed development data."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from depth_consistency import ConsistentContrasts
from longbaseline import sector_split
from multimode_cycle_experiment import weak
from parallel_bls import ParallelBoxLeastSquares
from physics import central_duration
from realistic_injections import make_loader

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / "reports/experiments/depth_consistency_diagnostic"
    folder.mkdir(exist_ok=True)
    source = ROOT / "reports/experiments/period_rank_diagnostic"
    plan = json.loads((source / "plan.json").read_text())
    hashes = dict(plan["source_sha256"])
    for name, digest in hashes.items():
        if sha(ROOT / name) != digest:
            raise ValueError(f"Source changed: {name}")
    for name in [
        "scripts/depth_consistency.py",
        "scripts/diagnose_depth_consistency.py",
        "docs/DIAGNOSTIC_DEPTH_CONSISTENCY.md",
        "reports/experiments/repeated_events/smoke_results.json",
    ]:
        hashes[name] = sha(ROOT / name)
    for case in plan["cases"]:
        for path in [
            source / (case["paired_id"] + ".json"),
            ROOT
            / "results/repeated_event_development"
            / ("leave_one_out__" + case["paired_id"])
            / "frozen_training.json",
        ]:
            hashes[str(path.relative_to(ROOT))] = sha(path)
    spec = dict(source_sha256=hashes, case_ids=[c["id"] for c in plan["cases"]], scope=__doc__)
    path = folder / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != v for k, v in spec.items()):
            raise ValueError("Preserve diagnostic")
    else:
        path.write_text(
            json.dumps(dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec), indent=2)
            + "\n"
        )
    stars = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC")
    summaries = []
    for case in plan["cases"]:
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
        contrast = ConsistentContrasts(training)
        model = ParallelBoxLeastSquares(
            training.time.to_numpy(), training.flux.to_numpy(), training.err.to_numpy()
        )
        seeds = json.loads((source / (case["paired_id"] + ".json")).read_text())["all_seeds"]
        fits = json.loads(
            (
                ROOT
                / "results/repeated_event_development"
                / ("leave_one_out__" + case["paired_id"])
                / "frozen_training.json"
            ).read_text()
        )["training_seed_diagnostics"]
        rows = []
        for record in fits:
            if record["iteration"] != 1:
                continue
            seed = seeds[record["global_rank"] - 1]
            if seed["period_days"] != record["coarse_period_days"]:
                raise ValueError("Different coarse seed")
            expected = central_duration(seed["period_days"], star)
            durations = np.unique(
                np.clip(
                    np.r_[
                        seed["duration_days"] * np.array([0.5, 0.75, 1]),
                        expected * np.array([0.5, 0.7, 1, 1.3]),
                    ],
                    0.015,
                    0.3,
                )
            )
            fitted = model.power(
                np.array([record["period_days"]]), durations, objective="likelihood", oversample=15
            )
            k = int(np.argmax(fitted.power))
            epoch = float(fitted.transit_time[k])
            duration = float(fitted.duration[k])
            period = record["period_days"]
            if (
                abs(duration - record["duration_days"]) > 1e-12
                or abs(float(fitted.depth_snr[k]) - record["nominal_training_snr"]) > 1e-8
            ):
                raise ValueError("Fixed-period replay did not reproduce original fine fit")
            measure = contrast.measure(period, epoch, duration)
            for key in ["total_snr", "leave_one_out_snr"]:
                if (
                    record["event_ranking"][key] is not None
                    and abs(measure[key] - record["event_ranking"][key]) > 1e-7
                ):
                    raise ValueError("Event-score replay mismatch")
            drift = []
            for t in [training.time.min(), training.time.max()]:
                center = epoch + round((t - epoch) / period) * period
                drift.append(
                    float(
                        abs(
                            (center - case["epoch_btjd"] + case["period_days"] / 2)
                            % case["period_days"]
                            - case["period_days"] / 2
                        )
                    )
                )
            rows.append(
                dict(
                    **record,
                    epoch_btjd=epoch,
                    consistency=measure,
                    true_timing_match=bool(
                        abs(period / case["period_days"] - 1) < 0.01
                        and max(drift) < 0.75 * case["duration_days"]
                    ),
                )
            )
        eligible = [r for r in rows if r["eligible"]]
        summary = dict(
            id=case["id"],
            replayed_fine_fits=len(rows),
            eligible_fine_fits=len(eligible),
            ranking={},
        )
        for metric in ["leave_one_out_snr", "consistent_total_snr", "consistent_leave_one_out_snr"]:
            order = sorted(eligible, key=lambda r: -r["consistency"][metric])
            summary["ranking"][metric] = dict(
                first_matching_rank=next(
                    (i for i, r in enumerate(order, 1) if r["true_timing_match"]), None
                ),
                best={
                    k: order[0][k]
                    for k in ["period_days", "duration_days", "consistency", "true_timing_match"]
                }
                if order
                else None,
            )
        (folder / (case["paired_id"] + ".json")).write_text(
            json.dumps(dict(summary, all_fits=rows), indent=2, allow_nan=False) + "\n"
        )
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    (folder / "results.json").write_text(
        json.dumps(
            dict(
                rows=summaries, completed_utc=datetime.now(timezone.utc).isoformat(), scope=__doc__
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
