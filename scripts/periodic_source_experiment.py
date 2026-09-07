"""Conditional pixel experiment with a measured periodic nuisance objective."""

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
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize

from cross_view_experiment import kernel
from multiscale_pixel_experiment import fit_weights as multiscale_weights
from protected_pixel_experiment import sigma
from relative_pixel_experiment import fit_weights as broad_weights, robust_covariance

ROOT = Path(__file__).resolve().parents[1]
TIC = 378527773
PERIOD = 0.37769418149605544
STAGES = {"development": [17, 58], "assessment": [18, 24, 25, 52]}


def load_sector(sector):
    manifest = json.loads((ROOT / f"data/targetpixels/{TIC}/manifest.json").read_text())
    records = [r for r in manifest["files"] if r["sector"] == sector]
    if len(records) != 1:
        raise ValueError("Require exactly one target-pixel product per sector")
    record = records[0]
    source = ROOT / record["path"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("Input hash mismatch")
    with fits.open(source, memmap=False) as h:
        if int(h[0].header["TICID"]) != TIC or int(h[0].header["SECTOR"]) != sector:
            raise ValueError("Target or sector identity mismatch")
        tab = h[1].data
        keep = np.isfinite(tab["TIME"]) & (tab["QUALITY"] == 0)
        t = np.asarray(tab["TIME"][keep], float)
        x = np.asarray(tab["FLUX"][keep], float)
        error = np.asarray(tab["FLUX_ERR"][keep], float)
        shape = x.shape[1:]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wcs = WCS(h[2].header)
        target = np.array(wcs.world_to_pixel_values(h[0].header["RA_OBJ"], h[0].header["DEC_OBJ"]))
        aperture = ((h[2].data.astype(int) & 2) > 0).ravel()
    x, error = x.reshape(len(t), -1), error.reshape(len(t), -1)
    valid = np.isfinite(x) & np.isfinite(error) & (error > 0)
    cut = float(np.median(t))
    pixels = valid[t <= cut].mean(axis=0) > 0.99
    rows = valid[:, pixels].all(axis=1)
    t, x, error = t[rows], x[rows][:, pixels], error[rows][:, pixels]
    bins = np.floor((t - t.min()) / (10 / 1440)).astype(int)
    counts = np.bincount(bins)
    occupied = counts > 0
    times = np.bincount(bins, weights=t)[occupied] / counts[occupied]
    values = np.column_stack(
        [np.bincount(bins, weights=c)[occupied] / counts[occupied] for c in x.T]
    )
    errors = np.column_stack(
        [np.sqrt(np.bincount(bins, weights=c * c)[occupied]) / counts[occupied] for c in error.T]
    )
    # Exclude a bin straddling the raw training boundary.
    training = times < cut - 10 / 1440
    held = times > cut + 10 / 1440
    return dict(
        t=times,
        x=values,
        error=errors,
        training=training,
        held=held,
        shape=shape,
        pixels=pixels,
        target=target,
        aperture=aperture[pixels],
        input=record,
    )


def harmonic_component(t, x, period):
    centered = t - np.mean(t)
    columns = [np.ones(len(t)), centered / max(np.ptp(t), 1)]
    for harmonic in [1, 2, 3]:
        angle = 2 * np.pi * harmonic * centered / period
        columns += [np.sin(angle), np.cos(angle)]
    design = np.column_stack(columns)
    coefficients = np.linalg.lstsq(design, x, rcond=None)[0]
    return design[:, 2:] @ coefficients[2:]


def fit_weights(t, training, profiles, noise_variance, baseline, period=PERIOD):
    b = np.asarray(baseline, float)
    n = np.diag(np.maximum(noise_variance, np.finfo(float).tiny))
    c = robust_covariance(training, noise_variance)
    d = robust_covariance(np.diff(training, axis=0) / np.sqrt(2), noise_variance)
    center = np.median(training, axis=0)
    scale = np.maximum(1.4826 * np.median(abs(training - center), axis=0), np.sqrt(noise_variance))
    clipped = np.clip(training - center, -8 * scale, 8 * scale)
    modeled = harmonic_component(t, clipped, period)
    periodic = modeled.T @ modeled / len(t)
    normalization = max(float(b @ periodic @ b), float(b @ n @ b) * 1e-10)
    periodic /= normalization
    caps = [m / float(b @ m @ b) for m in [n, d, c]]
    reference = profiles @ b
    if np.any(reference <= 0):
        raise ValueError("The reference aperture must respond positively to the target models")
    constraints = [LinearConstraint(profiles, reference, 1.03 * reference)]
    for m in caps:
        constraints.append(
            NonlinearConstraint(
                lambda w, m=m: float(w @ m @ w), -np.inf, 1.0, jac=lambda w, m=m: 2 * m @ w
            )
        )
    limit = max(2.0, 1.05 * float(np.max(abs(b))))
    solution = minimize(
        lambda w: float(w @ periodic @ w),
        b.copy(),
        jac=lambda w: 2 * periodic @ w,
        method="SLSQP",
        constraints=constraints,
        bounds=Bounds(-limit, limit),
        options=dict(maxiter=500, ftol=1e-10),
    )
    w = solution.x
    response = (profiles @ w) / reference
    feasible = bool(
        response.min() >= 1 - 1e-7
        and response.max() <= 1.03 + 1e-7
        and max(w @ m @ w for m in caps) <= 1 + 1e-7
        and np.max(abs(w)) <= limit + 1e-7
        and w @ periodic @ w <= b @ periodic @ b + 1e-7
    )
    fallback = None
    if not solution.success or not feasible:
        fallback = str(solution.message) if not solution.success else "Numerical constraint failure"
        w = b.copy()
    response = (profiles @ w) / reference
    return w, dict(
        fallback_reason=fallback,
        iterations=int(solution.nit),
        relative_response_min=float(response.min()),
        relative_response_max=float(response.max()),
        training_cap_ratios=[float(w @ m @ w) for m in caps],
        modeled_periodic_variance_ratio=float(w @ periodic @ w),
        covariance_sha256=hashlib.sha256(
            b"".join(m.tobytes() for m in caps + [periodic])
        ).hexdigest(),
    )


def compensated_residuals(t, y, minutes=120):
    bins = np.floor((t - t.min()) / (minutes / 1440)).astype(int)
    counts = np.bincount(bins)
    mean_t = np.bincount(bins, weights=t) / np.maximum(counts, 1)
    mean_y = np.bincount(bins, weights=y) / np.maximum(counts, 1)
    valid = counts >= minutes / 10 / 2
    keep = valid[:-2] & valid[1:-1] & valid[2:]
    a = (mean_t[1:-1][keep] - mean_t[:-2][keep]) / (mean_t[2:][keep] - mean_t[:-2][keep])
    residual = mean_y[1:-1][keep] - (1 - a) * mean_y[:-2][keep] - a * mean_y[2:][keep]
    return residual / np.sqrt(1 + (1 - a) ** 2 + a * a)


def process(sector, rng, out):
    data = load_sector(sector)
    t, x, error = (data[k] for k in ["t", "x", "error"])
    train, held = data["training"], data["held"]
    shape, target, pixels, aperture = (data[k] for k in ["shape", "target", "pixels", "aperture"])
    profiles = np.asarray(
        [
            kernel(shape, target + [dx, dy], (sx, sy)).ravel()[pixels]
            for dx, dy, sx, sy in itertools.product(
                [-0.2, 0, 0.2], [-0.2, 0, 0.2], [0.65, 0.85, 1.05], [0.65, 0.85, 1.05]
            )
        ]
    )
    p0 = kernel(shape, target, (0.85, 0.85)).ravel()[pixels]
    b = aperture.astype(float) / (aperture @ p0)
    noise = np.median(error[train] ** 2, axis=0)
    weights = {"aperture": b}
    diagnostics = {"aperture": dict(fallback_reason=None)}
    weights["broad"], diagnostics["broad"] = broad_weights(x[train], profiles, noise, b)
    weights["multiscale"], diagnostics["multiscale"] = multiscale_weights(
        t[train], x[train], profiles, noise, b
    )
    weights["periodic_source"], diagnostics["periodic_source"] = fit_weights(
        t[train], x[train], profiles, noise, b
    )
    frozen = dict(
        tic=TIC,
        sector=sector,
        input=data["input"],
        last_training_btjd=float(t[train][-1]),
        first_held_btjd=float(t[held][0]),
        training_points=int(train.sum()),
        held_points=int(held.sum()),
        target_xy=target.tolist(),
        selected_pixel_indices=np.flatnonzero(pixels).tolist(),
        weights={k: w.tolist() for k, w in weights.items()},
        diagnostics=diagnostics,
        frozen_utc=datetime.now(timezone.utc).isoformat(),
    )
    path = out / f"sector_{sector}_frozen.json"
    path.write_text(json.dumps(frozen, indent=2) + "\n")
    metrics = {}
    for name, w in weights.items():
        y = x[held] @ w
        residual = compensated_residuals(t[held], y)
        if len(residual) < 10:
            raise ValueError("Insufficient held two-hour windows")
        metrics[name] = dict(
            rapid_scatter=sigma(np.diff(y)) / np.sqrt(2),
            two_hour_scatter=sigma(residual),
            periodic_rms=float(np.std(harmonic_component(t[held], y, PERIOD))),
        )
    responses = {name: {"in_range": [], "wider_stress": []} for name in weights}
    for label, position, widths in [
        ("in_range", 0.2, (0.65, 1.05)),
        ("wider_stress", 0.35, (0.55, 1.2)),
    ]:
        for _ in range(250):
            p = kernel(
                shape, target + rng.uniform(-position, position, 2), rng.uniform(*widths, 2)
            ).ravel()[pixels]
            for name, w in weights.items():
                responses[name][label].append(float((w @ p) / (b @ p)))
    return dict(
        sector=sector,
        metrics=metrics,
        relative_responses=responses,
        weights_record=path.name,
        diagnostics=diagnostics,
    )


def gate(rows):
    ratios = lambda metric, comparison: [
        r["metrics"]["periodic_source"][metric] / r["metrics"][comparison][metric] for r in rows
    ]
    details = dict(
        median_two_hour_vs_aperture=float(np.median(ratios("two_hour_scatter", "aperture"))),
        median_two_hour_vs_broad=float(np.median(ratios("two_hour_scatter", "broad"))),
        median_two_hour_vs_multiscale=float(np.median(ratios("two_hour_scatter", "multiscale"))),
        worst_noise_vs_aperture=max(
            ratios("two_hour_scatter", "aperture") + ratios("rapid_scatter", "aperture")
        ),
        median_periodic_rms_vs_aperture=float(np.median(ratios("periodic_rms", "aperture"))),
        minimum_in_range_response=min(
            min(r["relative_responses"]["periodic_source"]["in_range"]) for r in rows
        ),
    )
    passed = (
        details["median_two_hour_vs_aperture"] <= 0.90
        and details["median_two_hour_vs_broad"] <= 0.95
        and details["median_two_hour_vs_multiscale"] <= 0.95
        and details["worst_noise_vs_aperture"] <= 1.05
        and details["median_periodic_rms_vs_aperture"] <= 0.70
        and details["minimum_in_range_response"] >= 0.99
    )
    return dict(passed=bool(passed), **details)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=STAGES, default="development")
    args = parser.parse_args()
    out = ROOT / "reports/experiments/periodic_source"
    out.mkdir(parents=True, exist_ok=True)
    sources = ["docs/EXPERIMENT_PERIODIC_SOURCE.md"] + [
        "scripts/" + p
        for p in [
            "periodic_source_experiment.py",
            "relative_pixel_experiment.py",
            "multiscale_pixel_experiment.py",
            "protected_pixel_experiment.py",
            "cross_view_experiment.py",
        ]
    ]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}
    manifest = json.loads((ROOT / f"data/targetpixels/{TIC}/manifest.json").read_text())
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609081,
        period_days=PERIOD,
        source_sha256=hashes,
        inputs=manifest["files"],
        stages=STAGES,
        scope="Conditional development on one inspected star; no discovery or novelty claim.",
    )
    plan_path = out / "plan.json"
    if plan_path.exists():
        old = json.loads(plan_path.read_text())
        if any(
            old[k] != plan[k] for k in ["source_sha256", "inputs", "stages", "seed", "period_days"]
        ):
            raise ValueError("Preserve the frozen experiment; source or inputs changed")
        plan = old
    else:
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    if (
        args.stage == "assessment"
        and not json.loads((out / "development.json").read_text())["gate"]["passed"]
    ):
        raise ValueError("Development gate failed; assessment is not authorized by this protocol")
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
                    diagnostics=row["diagnostics"]["periodic_source"],
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
