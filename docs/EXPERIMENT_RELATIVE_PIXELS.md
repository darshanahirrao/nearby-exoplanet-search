# Baseline-feasible, noise-capped pixel extraction

This development experiment follows the failed absolute-response extraction.
Its hypothesis is that the previous noise increase can be prevented while still
reducing contaminating variability by making the existing aperture a feasible
solution to every optimization constraint.

For pixel weights `w`, baseline aperture weights `b`, training covariance `C`,
nominal diagonal noise covariance `N`, training first-difference covariance `D`,
and modeled target footprints `p`, minimize `w.T C w` subject to:

- `p.T b <= p.T w <= 1.03 p.T b` for every modeled footprint;
- `w.T N w <= b.T N b`;
- `w.T D w <= b.T D b`;
- bounded weights that include `b`.

The baseline is feasible. Thus the exact constrained optimum cannot worsen the
training objective or either modeled noise variance, and it cannot attenuate a
target modeled by any convex mixture of the constrained footprints relative to
the baseline. This does not guarantee performance for unknown footprints,
nonstationary noise or actual reserved data. Numerical infeasibility or a worse
objective must fall back to the baseline and be reported explicitly.

Use the same eight sectors from the previous pixel experiment for development.
They have already been inspected; this is not fresh validation. Fit on their
first halves and evaluate their second halves with frozen weights. Report total
scatter, adjacent-difference scatter, compensated two-hour scatter, and response
to 500 random footprints per sector, including a wider mismatch stress range.
The two-hour statistic subtracts the mean of neighboring two-hour bins from the
middle bin and divides its robust scatter by sqrt(1.5).

Before any independent follow-up, require at least a 10% median reduction of the
two-hour statistic across the eight development sectors, no sector more than 5%
worse in either adjacent-difference or two-hour scatter, and less than 1% target
attenuation on the in-range random footprint draws. Report fallback frequency.
Passing this gate only warrants a fresh-data experiment; it cannot replace the
production pipeline or establish a discovery. Thresholds, seed, code and protocol
hashes are frozen before reading the new evaluation output.

Constrained minimum-variance estimation is established mathematics. This project
tests a particular response/noise constraint combination on these TESS inputs;
invention priority and astrophysical sensitivity gains are unestablished.
