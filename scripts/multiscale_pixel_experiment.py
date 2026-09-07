"""Baseline-feasible extraction targeting three transit-duration noise scales."""

from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize

from cross_view_experiment import FIELDS, kernel
from protected_pixel_experiment import load, sigma
from relative_pixel_experiment import compensated_scatter, robust_covariance

ROOT = Path(__file__).resolve().parents[1]


def compensated_pixels(t, x, minutes):
    residuals = []
    for offset in [0, 0.25, 0.5, 0.75]:
        bins = np.floor((t - t.min()) / (minutes / 1440) + offset).astype(int)
        counts = np.bincount(bins)
        means = np.column_stack(
            [np.bincount(bins, weights=col) / np.maximum(counts, 1) for col in x.T]
        )
        valid = counts >= minutes / 10 / 2
        keep = valid[:-2] & valid[1:-1] & valid[2:]
        residuals.append((means[1:-1] - (means[:-2] + means[2:]) / 2)[keep] / np.sqrt(1.5))
    residuals = np.concatenate(residuals)
    if len(residuals) < 20:
        raise ValueError("Insufficient contiguous training windows")
    return residuals


def fit_weights(t, x, profiles, noise_variance, baseline):
    b = np.asarray(baseline, float)
    noise = np.diag(np.maximum(noise_variance, np.finfo(float).tiny))
    rapid = robust_covariance(np.diff(x, axis=0) / np.sqrt(2), noise_variance)
    broad = robust_covariance(x, noise_variance)
    temporal = [
        robust_covariance(compensated_pixels(t, x, m), noise_variance / (m / 10))
        for m in [60, 120, 240]
    ]
    caps = [m / float(b @ m @ b) for m in [noise, rapid, broad]]
    temporal = [m / float(b @ m @ b) for m in temporal]
    reference = profiles @ b
    if np.any(reference <= 0):
        raise ValueError("Baseline has nonpositive modeled response")
    constraints = [
        LinearConstraint(
            np.column_stack([profiles, np.zeros(len(profiles))]), reference, 1.03 * reference
        )
    ]
    for m in caps:
        constraints.append(
            NonlinearConstraint(
                lambda u, m=m: float(u[:-1] @ m @ u[:-1]),
                -np.inf,
                1.0,
                jac=lambda u, m=m: np.r_[2 * m @ u[:-1], 0.0],
            )
        )
    for m in temporal:
        constraints.append(
            NonlinearConstraint(
                lambda u, m=m: float(u[:-1] @ m @ u[:-1] - u[-1]),
                -np.inf,
                0.0,
                jac=lambda u, m=m: np.r_[2 * m @ u[:-1], -1.0],
            )
        )
    limit = max(2.0, float(np.max(abs(b))) * 1.05)
    solution = minimize(
        lambda u: float(u[-1]),
        np.r_[b, 1.0],
        jac=lambda u: np.r_[np.zeros(len(b)), 1.0],
        method="SLSQP",
        constraints=constraints,
        bounds=Bounds(np.r_[np.full(len(b), -limit), 0.0], np.r_[np.full(len(b), limit), 1.0]),
        options=dict(maxiter=500, ftol=1e-10),
    )
    w = solution.x[:-1]
    response = (profiles @ w) / reference
    feasible = bool(
        response.min() >= 1 - 1e-7
        and response.max() <= 1.03 + 1e-7
        and max(w @ m @ w for m in caps + temporal) <= 1 + 1e-7
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
        training_cap_ratios=[float(w @ m @ w) for m in caps],
        training_temporal_variance_ratios=[float(w @ m @ w) for m in temporal],
        covariance_sha256=hashlib.sha256(
            b"".join(m.tobytes() for m in caps + temporal)
        ).hexdigest(),
    )


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
    w, diagnostics = fit_weights(
        t[:divide], x[:divide], profiles, np.median(error[:divide] ** 2, axis=0), b
    )
    record = dict(
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
    path.write_text(json.dumps(record, indent=2) + "\n")
    scatter = {}
    for name, weights in [("multiscale", w), ("fixed_aperture", b)]:
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
    ratios = {k: scatter["multiscale"][k] / v for k, v in scatter["fixed_aperture"].items()}
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
    out = ROOT / "reports/experiments/multiscale_pixels"
    out.mkdir(parents=True, exist_ok=True)
    paths = [
        "docs/EXPERIMENT_MULTISCALE_PIXELS.md",
        "scripts/multiscale_pixel_experiment.py",
        "scripts/relative_pixel_experiment.py",
        "scripts/protected_pixel_experiment.py",
        "scripts/cross_view_experiment.py",
    ]
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        seed=202609077,
        input_fields=FIELDS,
        file_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        development_gate=dict(
            median_two_hour_ratio_max=0.9,
            per_sector_noise_ratio_max=1.05,
            within_range_response_min=0.99,
        ),
        scope="Development on previously inspected sectors; independent validation and novelty unestablished.",
    )
    path = out / "plan.json"
    if path.exists():
        old = json.loads(path.read_text())
        if any(old[k] != plan[k] for k in ["seed", "file_sha256", "development_gate"]):
            raise ValueError("Preserve the original frozen experiment")
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
    (out / "results.json").write_text(
        json.dumps(
            dict(plan=plan, results=rows, failures=failures, development_gate_passed=gate), indent=2
        )
        + "\n"
    )
    print(json.dumps(dict(development_gate_passed=gate, completed=len(rows), failures=failures)))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
