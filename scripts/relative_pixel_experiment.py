"""Development trial of baseline-feasible response and noise constraints."""

from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize

from cross_view_experiment import FIELDS, kernel
from protected_pixel_experiment import load, sigma

ROOT = Path(__file__).resolve().parents[1]


def robust_covariance(x, floor):
    center = np.median(x, axis=0)
    scale = np.maximum(1.4826 * np.median(abs(x - center), axis=0), np.sqrt(floor))
    clipped = np.clip(x - center, -8 * scale, 8 * scale)
    c = np.atleast_2d(np.cov(clipped, rowvar=False))
    return 0.9 * c + 0.1 * np.diag(np.maximum(np.diag(c), floor))


def fit_weights(training, profiles, noise_variance, baseline):
    b = np.asarray(baseline, float)
    n = np.diag(np.maximum(noise_variance, np.finfo(float).tiny))
    c = robust_covariance(training, noise_variance)
    d = robust_covariance(np.diff(training, axis=0) / np.sqrt(2), noise_variance)
    c, n, d = [m / float(b @ m @ b) for m in (c, n, d)]
    reference = profiles @ b
    if np.any(reference <= 0):
        raise ValueError("Baseline must have positive response to all modeled targets")
    limit = max(2.0, float(np.max(abs(b))) * 1.05)
    constraints = [LinearConstraint(profiles, reference, 1.03 * reference)]
    for matrix in (n, d):
        constraints.append(
            NonlinearConstraint(
                lambda w, m=matrix: float(w @ m @ w),
                -np.inf,
                1.0,
                jac=lambda w, m=matrix: 2 * m @ w,
            )
        )
    solution = minimize(
        lambda w: float(w @ c @ w),
        b.copy(),
        jac=lambda w: 2 * c @ w,
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
        and max(w @ n @ w, w @ d @ w, w @ c @ w) <= 1 + 1e-7
        and np.max(abs(w)) <= limit + 1e-7
    )
    fallback = None
    if not solution.success or not feasible:
        fallback = str(solution.message) if not solution.success else "Numerical constraint failure"
        w = b.copy()
    response = (profiles @ w) / reference
    return w, dict(
        iterations=int(solution.nit),
        fallback_reason=fallback,
        relative_response_min=float(response.min()),
        relative_response_max=float(response.max()),
        training_variance_ratio=float(w @ c @ w),
        nominal_noise_variance_ratio=float(w @ n @ w),
        training_difference_variance_ratio=float(w @ d @ w),
        covariance_sha256=hashlib.sha256(c.tobytes() + n.tobytes() + d.tobytes()).hexdigest(),
    )


def compensated_scatter(t, y, minutes=120):
    bins = np.floor((t - t.min()) / (minutes / 1440)).astype(int)
    counts = np.bincount(bins)
    means = np.bincount(bins, weights=y) / np.maximum(counts, 1)
    valid = counts >= minutes / 10 / 2
    keep = valid[:-2] & valid[1:-1] & valid[2:]
    residual = (means[1:-1] - (means[:-2] + means[2:]) / 2)[keep]
    if len(residual) < 10:
        raise ValueError("Too few contiguous bins for the two-hour metric")
    return sigma(residual) / np.sqrt(1.5)


def process(tic, sector, rng, out):
    t, x, error, shape, pixels, target, aperture, source, digest = load(tic, sector)
    divide = len(t) // 2
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
    w, diagnostics = fit_weights(x[:divide], profiles, np.median(error[:divide] ** 2, axis=0), b)
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
        baseline_weights=b.tolist(),
        selected_pixel_indices=np.flatnonzero(pixels).tolist(),
        fitted_utc=datetime.now(timezone.utc).isoformat(),
        **diagnostics,
    )
    path = out / f"{tic}_{sector}_frozen.json"
    path.write_text(json.dumps(frozen, indent=2) + "\n")
    scatter = {}
    for name, weights in [("relative", w), ("fixed_aperture", b)]:
        y = x[divide:] @ weights
        scatter[name] = dict(
            robust_scatter=sigma(y),
            adjacent_difference_scatter=sigma(np.diff(y)) / np.sqrt(2),
            compensated_two_hour_scatter=compensated_scatter(t[divide:], y),
        )
    responses = {}
    for label, position, widths in [
        ("within_model_range", 0.2, (0.65, 1.05)),
        ("wider_stress_range", 0.35, (0.55, 1.2)),
    ]:
        values = []
        for _ in range(250):
            p = kernel(
                shape, target + rng.uniform(-position, position, 2), rng.uniform(*widths, 2)
            ).ravel()[pixels]
            values.append(float((w @ p) / (b @ p)))
        responses[label] = values
    ratios = {k: scatter["relative"][k] / v for k, v in scatter["fixed_aperture"].items()}
    return dict(
        tic=tic,
        sector=sector,
        weights_record=path.name,
        scatter=scatter,
        scatter_ratios=ratios,
        relative_response_draws=responses,
        **diagnostics,
    )


def main():
    out = ROOT / "reports/experiments/relative_pixels"
    out.mkdir(parents=True, exist_ok=True)
    files = [
        "docs/EXPERIMENT_RELATIVE_PIXELS.md",
        "scripts/relative_pixel_experiment.py",
        "scripts/protected_pixel_experiment.py",
        "scripts/cross_view_experiment.py",
    ]
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609076,
        input_fields=FIELDS,
        file_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files},
        development_gate=dict(
            median_two_hour_ratio_max=0.9,
            per_sector_noise_ratio_max=1.05,
            within_range_response_min=0.99,
        ),
        scope="Development on previously inspected sectors. No independent validation or novelty claim.",
    )
    path = out / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != plan[k] for k in ["seed", "file_sha256", "development_gate"]):
            raise ValueError("Experiment changed; preserve the original plan and results")
        plan = old
    else:
        path.write_text(json.dumps(plan, indent=2) + "\n")
    rng = np.random.default_rng(plan["seed"])
    rows, failures = [], []
    for tic, sectors in FIELDS.items():
        for sector in sectors:
            try:
                row = process(tic, sector, rng, out)
                rows.append(row)
                print(
                    json.dumps(
                        {k: row[k] for k in ["tic", "sector", "scatter_ratios", "fallback_reason"]}
                    ),
                    flush=True,
                )
            except Exception as exc:
                failures.append(dict(tic=tic, sector=sector, error=repr(exc)))
                print(json.dumps(failures[-1]), flush=True)
    gate = bool(
        rows
        and not failures
        and np.median([r["scatter_ratios"]["compensated_two_hour_scatter"] for r in rows]) <= 0.9
        and all(
            max(
                r["scatter_ratios"][k]
                for k in ["adjacent_difference_scatter", "compensated_two_hour_scatter"]
            )
            <= 1.05
            for r in rows
        )
        and all(min(r["relative_response_draws"]["within_model_range"]) >= 0.99 for r in rows)
    )
    report = dict(plan=plan, results=rows, failures=failures, development_gate_passed=gate)
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(development_gate_passed=gate, completed=len(rows), failures=failures)))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
