"""Constrained pixel extraction: a bounded experiment on existing public TPFs.

Fit on the first half of a sector; freeze weights before evaluating the second.
Preservation bounds cover the specified spatial models, not unknown real PRFs.
"""

from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from astropy.io import fits
from scipy.optimize import Bounds, LinearConstraint, minimize
from cross_view_experiment import FIELDS, kernel

ROOT = Path(__file__).resolve().parents[1]


def sigma(x):
    return float(1.4826 * np.median(abs(x - np.median(x))))


def fit_weights(training, profiles, noise_variance):
    center = np.median(training, axis=0)
    scale = 1.4826 * np.median(abs(training - center), axis=0)
    scale = np.maximum(scale, np.sqrt(noise_variance))
    centered = np.clip(training - center, -8 * scale, 8 * scale)
    covariance = np.cov(centered, rowvar=False)
    covariance = 0.9 * covariance + 0.1 * np.diag(np.maximum(np.diag(covariance), noise_variance))
    covariance += np.eye(len(covariance)) * np.trace(covariance) / len(covariance) * 1e-8
    covariance /= np.trace(covariance) / len(covariance)
    solution = minimize(
        lambda w: float(w @ covariance @ w),
        np.ones(training.shape[1]),
        jac=lambda w: 2 * covariance @ w,
        method="SLSQP",
        constraints=[LinearConstraint(profiles, 0.97, 1.03)],
        bounds=Bounds(-2, 2),
        options=dict(maxiter=500, ftol=1e-10),
    )
    response = profiles @ solution.x
    if not solution.success or response.min() < 0.97 - 1e-6 or response.max() > 1.03 + 1e-6:
        raise ValueError(
            f"Pixel optimization failed: {solution.message}; response {response.min()}-{response.max()}"
        )
    return solution.x, dict(
        iterations=int(solution.nit),
        constraint_min=float(response.min()),
        constraint_max=float(response.max()),
        training_covariance_sha256=hashlib.sha256(covariance.tobytes()).hexdigest(),
    )


def load(tic, sector):
    with np.load(ROOT / "results/cross_view" / f"{tic}_{sector}.npz", allow_pickle=False) as data:
        target = data["target"].copy()
        aperture = data["aperture"].copy()
        source = ROOT / str(data["source"])
        expected = str(data["sha256"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("TPF hash differs from the earlier reviewed input")
    with fits.open(source, memmap=False) as h:
        table = h[1].data
        keep = np.isfinite(table["TIME"]) & (table["QUALITY"] == 0)
        t = np.asarray(table["TIME"][keep], float)
        flux = np.asarray(table["FLUX"][keep], float)
        error = np.asarray(table["FLUX_ERR"][keep], float)
    shape = flux.shape[1:]
    flux = flux.reshape(len(t), -1)
    error = error.reshape(len(t), -1)
    valid = np.isfinite(flux) & np.isfinite(error) & (error > 0)
    pixels = valid.mean(axis=0) > 0.99
    rows = valid[:, pixels].all(axis=1)
    t, flux, error = t[rows], flux[rows][:, pixels], error[rows][:, pixels]
    # Fixed 10-minute bins. No clipping or detrending of the extracted signal.
    bins = np.floor((t - t.min()) / (10 / 1440)).astype(int)
    n = np.bincount(bins)
    occupied = n > 0
    times = np.bincount(bins, weights=t)[occupied] / n[occupied]
    values = np.column_stack(
        [np.bincount(bins, weights=col)[occupied] / n[occupied] for col in flux.T]
    )
    errors = np.column_stack(
        [np.sqrt(np.bincount(bins, weights=col**2)[occupied]) / n[occupied] for col in error.T]
    )
    return times, values, errors, shape, pixels, target, aperture.ravel()[pixels], source, expected


def process(tic, sector, rng, out):
    t, x, error, shape, pixels, target, aperture, source, digest = load(tic, sector)
    divide = len(t) // 2
    profiles = []
    for dx, dy, sx, sy in itertools.product(
        [-0.2, 0, 0.2], [-0.2, 0, 0.2], [0.65, 0.85, 1.05], [0.65, 0.85, 1.05]
    ):
        profiles.append(kernel(shape, target + [dx, dy], (sx, sy)).ravel()[pixels])
    profiles = np.asarray(profiles)
    w, diagnostics = fit_weights(x[:divide], profiles, np.median(error[:divide] ** 2, axis=0))
    p0 = kernel(shape, target, (0.85, 0.85)).ravel()[pixels]
    baseline = aperture.astype(float) / (aperture @ p0)
    frozen = dict(
        tic=tic,
        sector=sector,
        source=str(source.relative_to(ROOT)),
        source_sha256=digest,
        training_points=divide,
        held_points=len(t) - divide,
        last_training_btjd=float(t[divide - 1]),
        first_held_btjd=float(t[divide]),
        weights=w.tolist(),
        baseline_weights=baseline.tolist(),
        selected_pixel_indices=np.flatnonzero(pixels).tolist(),
        fitted_utc=datetime.now(timezone.utc).isoformat(),
        **diagnostics,
    )
    path = out / f"{tic}_{sector}_frozen.json"
    path.write_text(json.dumps(frozen, indent=2) + "\n")
    # Nothing above consults held-half flux when choosing weights.
    held = x[divide:]
    streams = {"protected": held @ w, "fixed_aperture": held @ baseline}
    scatter = {
        name: dict(
            robust_scatter=sigma(y), adjacent_difference_scatter=sigma(np.diff(y)) / np.sqrt(2)
        )
        for name, y in streams.items()
    }
    responses = {"within_model_range": [], "wider_stress_range": []}
    for label, position, widths in [
        ("within_model_range", 0.2, (0.65, 1.05)),
        ("wider_stress_range", 0.35, (0.55, 1.2)),
    ]:
        for _ in range(250):
            profile = kernel(
                shape, target + rng.uniform(-position, position, 2), rng.uniform(*widths, 2)
            ).ravel()[pixels]
            responses[label].append([float(w @ profile), float(baseline @ profile)])
    # Check a raw-pixel box injection using the already frozen linear operator.
    period = 7.311
    duration = 0.06
    epoch = t[divide] + rng.uniform(0, period)
    transit = abs((t[divide:] - epoch + period / 2) % period - period / 2) < duration / 2
    injection_profile = kernel(shape, target + [0.13, -0.11], (0.74, 0.96)).ravel()[pixels]
    amplitude = 2 * np.sqrt(np.median((error[divide:] ** 2) @ (baseline**2)))
    injected = held - amplitude * transit[:, None] * injection_profile[None, :]
    delta = (injected @ w) - (held @ w)
    predicted = -amplitude * transit * (w @ injection_profile)
    mismatch = float(np.max(abs(delta - predicted)))
    if not np.allclose(delta, predicted, rtol=1e-9, atol=1e-9):
        raise ValueError("Raw injection does not match the frozen operator's predicted response")
    result = dict(
        tic=tic,
        sector=sector,
        weights_record=path.name,
        scatter=scatter,
        response_draws=responses,
        raw_injection_max_absolute_error=mismatch,
        injected_held_samples=int(transit.sum()),
        injected_target_response=float(w @ injection_profile),
        baseline_injected_target_response=float(baseline @ injection_profile),
        **diagnostics,
    )
    return result


def main():
    out = ROOT / "reports/experiments/protected_pixels"
    out.mkdir(parents=True, exist_ok=True)
    protocol = ROOT / "docs/EXPERIMENT_PROTECTED_PIXELS.md"
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609075,
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        configuration=dict(
            covariance_diagonal_shrinkage=0.1,
            weights_bounds=[-2, 2],
            preservation_bounds=[0.97, 1.03],
            training_fraction=0.5,
            bin_minutes=10,
        ),
        claim="Experimental target-response-preserving extraction. No validated sensitivity gain, invention priority or discovery.",
    )
    path = out / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(
            old[k] != plan[k] for k in ["seed", "code_sha256", "protocol_sha256", "configuration"]
        ):
            raise ValueError("Experiment changed; preserve original results")
        plan = old
    else:
        path.write_text(json.dumps(plan, indent=2) + "\n")
    rng = np.random.default_rng(plan["seed"])
    rows = []
    failures = []
    for tic, sectors in FIELDS.items():
        for sector in sectors:
            try:
                row = process(tic, sector, rng, out)
                rows.append(row)
                compact = {
                    k: row[k]
                    for k in [
                        "tic",
                        "sector",
                        "scatter",
                        "constraint_min",
                        "constraint_max",
                        "injected_target_response",
                    ]
                }
                print(json.dumps(compact), flush=True)
            except Exception as exc:
                failure = dict(tic=tic, sector=sector, error=repr(exc))
                failures.append(failure)
                print(json.dumps(failure), flush=True)
    (out / "results.json").write_text(
        json.dumps(dict(plan=plan, results=rows, failures=failures), indent=2) + "\n"
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
