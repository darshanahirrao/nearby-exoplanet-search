"""Fixed-timing local polynomial continuum diagnostics, not a search or FAP test.

Fit the continuum outside a protected event window. Propagate its weighted
least-squares covariance into the predicted mean inside the event. Errors remain
nominal: temporal covariance and errors in the continuum model are not included.
"""

import numpy as np


def continuum_event(frame, center, duration, degree=2, width_scale=1.0):
    x = (frame.time.to_numpy() - center) / duration
    flux = frame.flux.to_numpy() - 1
    error = frame.err.to_numpy()
    outer = max(4 * duration, 0.3) * width_scale / duration
    inside = np.abs(x) < 0.5
    left = (x < -1) & (x > -outer)
    right = (x > 1) & (x < outer)
    record = dict(
        center_btjd=float(center),
        degree=degree,
        width_scale=width_scale,
        inside_points=int(inside.sum()),
        left_points=int(left.sum()),
        right_points=int(right.sum()),
        outer_days=float(outer * duration),
    )
    # A polynomial extrapolation from just one side is deliberately not reported.
    if inside.sum() < 3 or left.sum() < 4 or right.sum() < 4:
        return record | dict(status="insufficient_two_sided_coverage")
    outside = left | right
    design = np.polynomial.polynomial.polyvander(x[outside], degree)
    weighted_design = design / error[outside, None]
    if np.linalg.matrix_rank(weighted_design) != degree + 1:
        return record | dict(status="singular_baseline")
    covariance = np.linalg.inv(weighted_design.T @ weighted_design)
    coefficient = np.linalg.lstsq(weighted_design, flux[outside] / error[outside], rcond=None)[0]
    wi = 1 / error[inside] ** 2
    prediction = np.average(
        np.polynomial.polynomial.polyvander(x[inside], degree), axis=0, weights=wi
    )
    depth = float(prediction @ coefficient - np.average(flux[inside], weights=wi))
    depth_error = float(np.sqrt(prediction @ covariance @ prediction + 1 / wi.sum()))
    flanks = {}
    for name, selection in [("left", left), ("right", right)]:
        weights = 1 / error[selection] ** 2
        flank_depth = float(
            np.average(flux[selection], weights=weights) - np.average(flux[inside], weights=wi)
        )
        flank_error = float(np.sqrt(1 / weights.sum() + 1 / wi.sum()))
        flanks[name] = dict(depth=flank_depth, error=flank_error, snr=flank_depth / flank_error)
    residual = flux[outside] - design @ coefficient
    return record | dict(
        status="measured",
        depth=depth,
        error=depth_error,
        snr=depth / depth_error,
        coefficients=coefficient.tolist(),
        nominal_baseline_reduced_chi2=float(
            np.sum((residual / error[outside]) ** 2) / (outside.sum() - degree - 1)
        ),
        flanks=flanks,
    )


def combine_events(events, flank=None):
    measured = [
        e if flank is None else e["flanks"][flank] for e in events if e["status"] == "measured"
    ]
    if not measured:
        return dict(events=0, positive_events=0, depth=None, error=None, nominal_snr=None)
    depths = np.array([e["depth"] for e in measured])
    weights = 1 / np.array([e["error"] for e in measured]) ** 2
    mean = float(np.average(depths, weights=weights))
    error = float(1 / np.sqrt(weights.sum()))
    return dict(
        events=len(measured),
        positive_events=int(np.sum(depths > 0)),
        depth=mean,
        error=error,
        nominal_snr=mean / error,
    )


def continuum_train(frame, period, epoch, duration, degree=2, width_scale=1.0):
    time = frame.time.to_numpy()
    phase = (time - epoch + period / 2) % period - period / 2
    cycles = np.unique(np.rint((time[np.abs(phase) < duration / 2] - epoch) / period).astype(int))
    events = [
        dict(
            cycle=int(c),
            **continuum_event(frame, epoch + c * period, duration, degree, width_scale),
        )
        for c in cycles
    ]
    return dict(
        **combine_events(events),
        event_measurements=events,
        rejected_for_coverage=sum(e["status"] == "insufficient_two_sided_coverage" for e in events),
        left_only=combine_events(events, "left"),
        right_only=combine_events(events, "right"),
    )
