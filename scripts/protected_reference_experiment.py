"""A linear source-reference filter with finite-model transit response bounds."""

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from cross_view_experiment import kernel
from periodic_source_experiment import load_sector, compensated_residuals, harmonic_component
from protected_pixel_experiment import sigma

ROOT = Path(__file__).resolve().parents[1]
PERIOD = 0.37769418149605544
NEIGHBOR_RADEC = (0.440267096131202, 69.5015238397358)
STAGES = {"development": [17, 58], "assessment": [18, 24, 25, 52]}


def reference_weights(target, neighbor, noise):
    a = np.column_stack([target, neighbor])
    inv = 1 / np.maximum(noise, np.finfo(float).tiny)
    gram = a.T @ (inv[:, None] * a)
    if np.linalg.cond(gram) > 1e10:
        return np.zeros_like(target), "Spatial models cannot be separated numerically"
    q = inv * (a @ np.linalg.solve(gram, np.array([0.0, 1.0])))
    if max(abs(q @ target), abs(q @ neighbor - 1)) > 1e-8:
        raise ValueError("Reference response constraints failed")
    return q, None


def bases(t):
    dt = (t - np.mean(t)) / np.ptp(t)
    trend = np.linalg.qr(np.column_stack([np.ones(len(t)), dt]))[0]
    angle = 2 * np.pi * (t - t.min()) / PERIOD
    raw = np.column_stack([f(k * angle) for k in [1, 2, 3] for f in [np.sin, np.cos]])
    raw -= trend @ (trend.T @ raw)
    q = np.linalg.qr(raw)[0]
    return trend, q


def transit(t, period, epoch, duration, shape):
    distance = abs((t - epoch + period / 2) % period - period / 2)
    if shape == "box":
        return (distance < duration / 2).astype(float)
    return np.clip((duration / 2 - distance) / (duration / 4), 0, 1)


def projection_fraction(u, trend, modes):
    denominator = float(u @ u - np.sum((trend.T @ u) ** 2))
    if denominator <= 1e-8:
        return None
    return float(np.sum((modes.T @ u) ** 2) / denominator)


def temporal_certificate(t, trend, modes):
    periods = np.unique(np.r_[np.geomspace(3, 40, 24), PERIOD * np.arange(8, int(40 / PERIOD) + 1)])
    maximum, count = 0.0, 0
    for period in periods:
        vectors = []
        for phase, duration, shape in itertools.product(
            np.arange(8) / 8, [0.025, 0.05, 0.10, 0.15], ["box", "trapezoid"]
        ):
            u = transit(t, period, t.min() + phase * period, duration, shape)
            if np.count_nonzero(u) >= 3:
                vectors.append(u)
        if not vectors:
            continue
        matrix = np.column_stack(vectors)
        denominator = np.sum(matrix * matrix, axis=0) - np.sum((trend.T @ matrix) ** 2, axis=0)
        valid = denominator > 1e-8
        fractions = np.sum((modes.T @ matrix) ** 2, axis=0)[valid] / denominator[valid]
        maximum = max(maximum, float(fractions.max()))
        count += len(fractions)
    return maximum, count


def apply(x, b, q, modes, coefficient):
    return x @ b - coefficient * (modes @ (modes.T @ (x @ q)))


def diagonal_noise(error, b, q, modes, coefficient):
    vb = (error**2) @ (b * b)
    vq = (error**2) @ (q * q)
    cross = (error**2) @ (b * q)
    small = modes.T @ (vq[:, None] * modes)
    added = np.sum((modes @ small) * modes, axis=1)
    result = vb + coefficient**2 * added - 2 * coefficient * np.sum(modes * modes, axis=1) * cross
    if np.any(result <= 0):
        raise ValueError("Invalid propagated noise variance")
    return result


def process(sector, rng, out):
    data = load_sector(sector)
    with fits.open(ROOT / data["input"]["path"], memmap=True) as h:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            neighbor = np.array(WCS(h[2].header).world_to_pixel_values(*NEIGHBOR_RADEC))
    target, pixels, shape = data["target"], data["pixels"], data["shape"]
    p = kernel(shape, target, (0.85, 0.85)).ravel()[pixels]
    n = kernel(shape, neighbor, (0.85, 0.85)).ravel()[pixels]
    aperture = data["aperture"].astype(float)
    b = aperture / (aperture @ p)
    q, fallback = reference_weights(p, n, np.median(data["error"][data["training"]] ** 2, axis=0))
    profiles = np.asarray(
        [
            kernel(shape, target + [dx, dy], (sx, sy)).ravel()[pixels]
            for dx, dy, sx, sy in itertools.product(
                [-0.2, 0, 0.2], [-0.2, 0, 0.2], [0.65, 0.85, 1.05], [0.65, 0.85, 1.05]
            )
        ]
    )
    held = data["held"]
    t = data["t"][held]
    trend, modes = bases(t)
    factor, count = temporal_certificate(t, trend, modes)
    beta = float(b @ n)
    leakage = beta * (profiles @ q) / (profiles @ b)
    worst = max(0.0, float(leakage.max())) * factor
    strength = min(1.0, 0.01 / worst) if worst > 0 else 1.0
    if fallback:
        strength = 0.0
    coefficient = strength * beta
    frozen = dict(
        sector=sector,
        input=data["input"],
        target_xy=target.tolist(),
        neighbor_xy=neighbor.tolist(),
        b=b.tolist(),
        q=q.tolist(),
        coefficient=coefficient,
        strength=strength,
        fallback_reason=fallback,
        last_training_btjd=float(data["t"][data["training"]][-1]),
        first_held_btjd=float(t[0]),
        finite_temporal_models=count,
        maximum_projection_fraction=factor,
        maximum_spatial_leakage=float(leakage.max()),
        certified_minimum_response=1 - strength * worst,
        selected_pixel_indices=np.flatnonzero(pixels).tolist(),
        temporal_basis_sha256=hashlib.sha256(trend.tobytes() + modes.tobytes()).hexdigest(),
        frozen_utc=datetime.now(timezone.utc).isoformat(),
    )
    path = out / f"sector_{sector}_frozen.json"
    path.write_text(json.dumps(frozen, indent=2) + "\n")
    x, error = data["x"][held], data["error"][held]
    raw = x @ b
    curves = dict(
        aperture=raw,
        temporal_only=raw - modes @ (modes.T @ raw),
        protected_reference=apply(x, b, q, modes, coefficient),
    )
    metrics = {}
    for name, y in curves.items():
        metrics[name] = dict(
            rapid_scatter=sigma(np.diff(y)) / np.sqrt(2),
            two_hour_scatter=sigma(compensated_residuals(t, y)),
            periodic_rms=float(np.std(harmonic_component(t, y, PERIOD))),
        )
    responses = []
    for i in range(300):
        profile = kernel(
            shape, target + rng.uniform(-0.2, 0.2, 2), rng.uniform(0.65, 1.05, 2)
        ).ravel()[pixels]
        period = (
            PERIOD * int(rng.integers(8, 107))
            if i % 2 == 0
            else float(np.exp(rng.uniform(np.log(3), np.log(40))))
        )
        duration = float(rng.uniform(0.025, 0.15))
        epoch = float(t.min() + rng.uniform(0, period))
        u = transit(t, period, epoch, duration, "trapezoid" if i % 3 else "box")
        f = projection_fraction(u, trend, modes)
        if f is None or np.count_nonzero(u) < 3:
            continue
        response = 1 - coefficient * (q @ profile) / (b @ profile) * f
        # Explicitly verify the formula against an injected pixel signal.
        filtered = apply(u[:, None] * profile, b, q, modes, coefficient)
        residual_u = u - trend @ (trend.T @ u)
        measured = float(residual_u @ filtered / (residual_u @ u) / (b @ profile))
        if not np.isclose(response, measured, rtol=1e-9, atol=1e-10):
            raise ValueError("Analytic transfer response disagrees with pixel operator")
        responses.append(
            dict(
                period_days=period,
                duration_days=duration,
                epoch_btjd=epoch,
                protected_response=float(response),
                temporal_only_response=1 - f,
            )
        )
    variance = diagonal_noise(error, b, q, modes, coefficient)
    return dict(
        sector=sector,
        metrics=metrics,
        unseen_responses=responses,
        median_photon_noise_ratio=float(np.median(np.sqrt(variance / ((error**2) @ (b * b))))),
        weights_record=path.name,
        operator=frozen,
    )


def gate(rows):
    ratios = lambda metric, comparison: [
        r["metrics"]["protected_reference"][metric] / r["metrics"][comparison][metric] for r in rows
    ]
    details = dict(
        median_two_hour_vs_aperture=float(np.median(ratios("two_hour_scatter", "aperture"))),
        worst_noise_vs_aperture=max(
            ratios("two_hour_scatter", "aperture") + ratios("rapid_scatter", "aperture")
        ),
        median_periodic_rms_vs_aperture=float(np.median(ratios("periodic_rms", "aperture"))),
        median_two_hour_vs_temporal=float(np.median(ratios("two_hour_scatter", "temporal_only"))),
        minimum_unseen_response=min(
            s["protected_response"] for r in rows for s in r["unseen_responses"]
        ),
    )
    passed = (
        details["median_two_hour_vs_aperture"] <= 0.9
        and details["worst_noise_vs_aperture"] <= 1.05
        and details["median_periodic_rms_vs_aperture"] <= 0.5
        and details["median_two_hour_vs_temporal"] <= 1.05
        and details["minimum_unseen_response"] >= 0.99
    )
    return dict(passed=bool(passed), **details)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=STAGES, default="development")
    args = parser.parse_args()
    out = ROOT / "reports/experiments/protected_reference"
    out.mkdir(parents=True, exist_ok=True)
    files = ["docs/EXPERIMENT_PROTECTED_REFERENCE.md"] + [
        "scripts/" + p
        for p in [
            "protected_reference_experiment.py",
            "periodic_source_experiment.py",
            "relative_pixel_experiment.py",
            "multiscale_pixel_experiment.py",
            "protected_pixel_experiment.py",
            "cross_view_experiment.py",
        ]
    ]
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609082,
        period_days=PERIOD,
        neighbor_radec=list(NEIGHBOR_RADEC),
        stages=STAGES,
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files},
        inputs=json.loads((ROOT / "data/targetpixels/378527773/manifest.json").read_text())[
            "files"
        ],
        scope="Conditional development and finite-model certificate, not general transit validation or novelty.",
    )
    path = out / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(
            old[k] != plan[k]
            for k in ["seed", "period_days", "neighbor_radec", "stages", "source_sha256", "inputs"]
        ):
            raise ValueError("Preserve the frozen plan; source or configuration changed")
        plan = old
    else:
        path.write_text(json.dumps(plan, indent=2) + "\n")
    if (
        args.stage == "assessment"
        and not json.loads((out / "development.json").read_text())["gate"]["passed"]
    ):
        raise ValueError(
            "The development gate failed; do not evaluate additional views under this protocol"
        )
    rng = np.random.default_rng(plan["seed"] + (args.stage == "assessment"))
    rows = []
    for sector in STAGES[args.stage]:
        row = process(sector, rng, out)
        rows.append(row)
        print(
            json.dumps(
                dict(
                    sector=sector,
                    metrics=row["metrics"],
                    strength=row["operator"]["strength"],
                    photon_noise_ratio=row["median_photon_noise_ratio"],
                    minimum_response=min(s["protected_response"] for s in row["unseen_responses"]),
                )
            ),
            flush=True,
        )
    report = dict(
        stage=args.stage,
        completed_utc=datetime.now(timezone.utc).isoformat(),
        results=rows,
        gate=gate(rows),
    )
    (out / f"{args.stage}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["gate"]), flush=True)


if __name__ == "__main__":
    main()
