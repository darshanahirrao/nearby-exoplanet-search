"""Separate frozen-view prediction from ordinary spatial template fitting.

Fresh random seed; same finite real-noise banks as the prototype. This is an
ablation of a map-level experiment, not an independent telescope survey.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import cross_view_experiment as experiment

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = experiment.evaluate


def evaluate(frames, images):
    row = ORIGINAL(frames, images)
    scores = [frame.scores(image) for frame, image in zip(frames, images)]
    held = scores[-1]
    held_best = int(np.argmax(held))
    held_distance = np.linalg.norm(experiment.GRID[held_best]) / experiment.PIXEL_ARCSEC
    target_index = frames[0].target_index
    fixed_training = np.sqrt(sum(max(0, z[target_index]) ** 2 for z in scores[:-1]))
    row.update(
        refit_held_accept=bool(
            row["training_nominal_snr"] >= 7
            and held[held_best] >= 5
            and row["predicted_offset_nominal_pixels"] <= 0.5
            and held_distance <= 0.5
        ),
        target_fixed_accept=bool(fixed_training >= 7 and held[target_index] >= 5),
    )
    return row


def main():
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609073,
        cases=900,
        experiment_code_sha256=hashlib.sha256(Path(experiment.__file__).read_bytes()).hexdigest(),
        ablation_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        hypothesis="Measure whether frozen-view prediction adds recovery beyond the same spatial filter with a newly fitted held-view position.",
        thresholds="Unchanged training SNR 7, held SNR 5, maximum position offset 0.5 nominal pixels.",
        limitations="Fresh injection draws but reused off-event noise banks and related Gaussian injection/fit families; not raw-pixel sensitivity or established novelty.",
    )
    out = ROOT / "reports/experiments/cross_view"
    destination = out / "ablation_plan.json"
    if destination.exists():
        old = json.loads(destination.read_text())
        if any(
            old[key] != plan[key]
            for key in ["seed", "cases", "experiment_code_sha256", "ablation_code_sha256"]
        ):
            raise ValueError("Ablation configuration changed; use a separate experiment record")
        plan = old
    else:
        destination.write_text(json.dumps(plan, indent=2) + "\n")
    fields = {
        tic: experiment.prepare(tic, sectors)[0] for tic, sectors in experiment.FIELDS.items()
    }
    experiment.evaluate = evaluate
    rows = experiment.trials(fields, plan["seed"], plan["cases"], True)
    modes = ["cross_view_accept", "refit_held_accept", "target_fixed_accept", "baseline_accept"]
    report = {
        label: dict(
            cases=sum(row["label"] == label for row in rows),
            **{mode: sum(row[mode] for row in rows if row["label"] == label) for mode in modes},
        )
        for label in ["target", "displaced", "no_injection"]
    }
    report["paired_target_comparison"] = dict(
        frozen_only=sum(
            row["cross_view_accept"] and not row["refit_held_accept"]
            for row in rows
            if row["label"] == "target"
        ),
        refit_only=sum(
            row["refit_held_accept"] and not row["cross_view_accept"]
            for row in rows
            if row["label"] == "target"
        ),
    )
    (out / "ablation.json").write_text(
        json.dumps(dict(plan=plan, summary=report, trials=rows), indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
