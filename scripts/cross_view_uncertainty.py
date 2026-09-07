"""Test a training-weighted spatial predictor instead of a single fitted position.

Profile-likelihood weights are a heuristic, not a calibrated source posterior.
All thresholds are fixed before this experiment. Original methods are unchanged.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import shift
from scipy.special import softmax
import cross_view_experiment as experiment
import cross_view_ablation as ablation

ROOT = Path(__file__).resolve().parents[1]


def predictor(training_frames, training_images, reserved_frame):
    score = np.sum(
        [
            np.maximum(frame.scores(image), 0) ** 2
            for frame, image in zip(training_frames, training_images)
        ],
        axis=0,
    )
    weights = softmax(0.5 * score)
    mean_template = weights @ reserved_frame.models
    mean_template /= np.linalg.norm(mean_template)
    near = np.linalg.norm(experiment.GRID, axis=1) <= 0.5 * experiment.PIXEL_ARCSEC
    return mean_template, dict(
        training_nominal_snr=float(np.sqrt(score.max())),
        training_near_target_weight=float(weights[near].sum()),
        effective_grid_positions=float(1 / (weights @ weights)),
        frozen_weights_sha256=hashlib.sha256(weights.tobytes()).hexdigest(),
        frozen_predictor_sha256=hashlib.sha256(mean_template.tobytes()).hexdigest(),
    )


def evaluate(frames, images):
    predicted, frozen = predictor(frames[:-1], images[:-1], frames[-1])
    held_snr = float(predicted @ frames[-1].whiten(images[-1]))
    row = ablation.evaluate(frames, images)
    row.update(frozen)
    row.update(
        uncertainty_held_nominal_snr=held_snr,
        uncertainty_accept=bool(
            frozen["training_nominal_snr"] >= 7
            and frozen["training_near_target_weight"] >= 0.5
            and held_snr >= 5
        ),
    )
    return row


def empirical_shape(frame, xy):
    """Shift an observed positive deficit core; includes response mismatch and noise."""
    data = frame.data["actual"]
    good = frame.good & np.isfinite(data)
    snr = np.where(good, data / frame.error, -np.inf)
    py, px = np.unravel_index(np.argmax(snr), data.shape)
    yy, xx = np.indices(data.shape)
    core = good & (abs(xx - px) <= 2) & (abs(yy - py) <= 2)
    template = np.where(core, np.maximum(data, 0), 0)
    center = np.array([(xx * template).sum(), (yy * template).sum()]) / template.sum()
    # This is an empirical stress shape, not an independently measured stellar PRF.
    return shift(template, (xy[1] - center[1], xy[0] - center[0]), order=1, mode="constant", cval=0)


def run(fields, seed, count):
    rng = np.random.default_rng(seed)
    rows = []
    labels = ["target", "displaced", "no_injection"]
    for index in range(count):
        tic = list(fields)[index % 3]
        frames = fields[tic]
        shape_kind = "gaussian" if (index // 3) % 2 == 0 else "empirical_core"
        label = labels[(index // 6) % 3]
        strength = float(rng.uniform(3, 12))
        angle = rng.uniform(0, 2 * np.pi)
        separation = float(rng.uniform(0.25, 3)) if label == "displaced" else 0
        offset = separation * experiment.PIXEL_ARCSEC * np.array([np.cos(angle), np.sin(angle)])
        widths = rng.uniform(0.6, 1.0, 2)
        images = []
        for frame in frames:
            bank = frame.data["null"][1::2]
            image = bank[rng.integers(len(bank))].copy()
            if label != "no_injection":
                xy = frame.xy(offset) + rng.normal(0, 0.05, 2)
                if shape_kind == "gaussian":
                    shape = experiment.kernel(frame.shape, xy, widths * rng.uniform(0.9, 1.1, 2))
                else:
                    shape = empirical_shape(frame, xy)
                norm = np.linalg.norm(frame.whiten(shape))
                image += shape * (strength * rng.uniform(0.9, 1.1) / norm)
            images.append(image)
        rows.append(
            dict(
                tic=tic,
                trial=index,
                label=label,
                shape_kind=shape_kind,
                injected_separation_pixels=separation,
                injected_snr_per_view=strength,
                **evaluate(frames, images),
            )
        )
    return rows


def summarize(rows):
    modes = [
        "uncertainty_accept",
        "cross_view_accept",
        "refit_held_accept",
        "target_fixed_accept",
        "baseline_accept",
    ]
    summary = {}
    for shape in ["gaussian", "empirical_core"]:
        subset = [r for r in rows if r["shape_kind"] == shape]
        summary[shape] = {
            label: dict(
                cases=sum(r["label"] == label for r in subset),
                **{mode: sum(r[mode] for r in subset if r["label"] == label) for mode in modes},
            )
            for label in ["target", "displaced", "no_injection"]
        }
        targets = [r for r in subset if r["label"] == "target"]
        summary[shape]["paired_vs_refit"] = dict(
            uncertainty_only=sum(
                r["uncertainty_accept"] and not r["refit_held_accept"] for r in targets
            ),
            refit_only=sum(r["refit_held_accept"] and not r["uncertainty_accept"] for r in targets),
        )
    return summary


def main():
    out = ROOT / "reports/experiments/cross_view_uncertainty"
    out.mkdir(parents=True, exist_ok=True)
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609074,
        cases=1800,
        hypothesis="Retain a distribution of training positions and predict a reserved-view spatial template; test whether this preserves more signals than refitting or a frozen point position.",
        thresholds=dict(
            training_snr=7, near_target_weight=0.5, held_snr=5, target_radius_pixels=0.5
        ),
        profile_weights="softmax(0.5 * sum positive training pixel-template SNR squared), uniform grid weight; heuristic, not calibrated posterior probability",
        comparisons="Same spatial filter refitting the reserved-view position, previous frozen-position method, fixed-target filter, and simple aperture/centroid diagnostic.",
        source_code_sha256={
            name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
            for name in [
                "cross_view_uncertainty.py",
                "cross_view_experiment.py",
                "cross_view_ablation.py",
            ]
        },
        limitations="Fresh injection draws, reused finite real-noise banks. Map-level injections with Gaussian and empirical positive-core shapes; not raw-pixel planet recovery or established novelty. Displaced cases include unresolved close blends.",
    )
    path = out / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != plan[k] for k in ["seed", "cases", "source_code_sha256", "thresholds"]):
            raise ValueError("Experiment changed; preserve prior plan")
        plan = old
    else:
        path.write_text(json.dumps(plan, indent=2) + "\n")
    fields = {
        tic: experiment.prepare(tic, sectors)[0] for tic, sectors in experiment.FIELDS.items()
    }
    rows = run(fields, plan["seed"], plan["cases"])
    summary = summarize(rows)
    (out / "results.json").write_text(
        json.dumps(dict(plan=plan, summary=summary, trials=rows), indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
