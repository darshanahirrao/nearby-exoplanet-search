# Cycle-excluded templates gained one strict injection recovery

The completed development experiment ran 27 faint raw-light-curve injections and three unmodified-star diagnostics through each of three filters: 90 runs total. All runs finished without errors. The original combined-season period grid, two retained peaks, and training/held-sector checks were shared.

| Filter | Injected signals recovered | Also passed strict checks | Unflagged fits in three unmodified stars |
| --- | ---: | ---: | ---: |
| Production three-harmonic filter | 6 / 27 | 5 / 27 | 1 |
| Same filter, lower power threshold | 6 / 27 | 5 / 27 | 1 |
| Cycle-excluded median template | 7 / 27 | 6 / 27 | 1 |

The new variant recovered one additional strict case, `232970271_orbit1_radius1`, and lost none of the strict recoveries made by either comparison. However, the preregistered gate required at least two additional strict recoveries over the stronger comparison. The gate failed; this method remains experimental and is not adopted. One additional synthetic recovery is not evidence for a new planet or a reliable general advantage.

These cases deliberately include smaller radii (0.6, 0.8 and 1.0 Earth radii) on three variable development stars. Their recovery counts must not be compared directly with earlier suites using different stars, radii, periods and phases. Box injections favor BLS and omit upstream SPOC signal losses. Three unmodified stars cannot calibrate a false-alarm probability, and an unflagged fit is not a planet.

For a fixed stellar period, an offline check verifies that a dip inserted in one cycle does not change that cycle group's fitted template. The stellar-period estimate can still respond to the injection; full injection runs refit the entire preprocessing stage rather than assuming protection.

Rotation-template detrending has prior art, including [LOCoR](https://acrizzuto.wixsite.com/astro/research). The present implementation is a project-specific variation, not an established methodological invention.

- [Frozen protocol](../../../docs/EXPERIMENT_CYCLE_EXCLUDED.md)
- [Exact cases and source hashes](plan.json)
- [Paired results and losses](results.json)
- [Filter implementation](../../../scripts/cycle_excluded.py)
- [Benchmark driver](../../../scripts/cycle_excluded_experiment.py)

Reproduce with `python scripts/cycle_excluded_experiment.py --workers 3` after downloading the listed stars' SPOC light curves. Raw result artifacts remain local and their hashes are listed in the compact results.

The [post-result missed-injection diagnosis](missed_wolf_injection_diagnostic.json)
found two Wolf 1069 injections with nominal training S/N above 7 and held-sector
S/N above 5, with enough events, when evaluated at their known injected periods.
Neither was recovered blindly. [Retaining eight ordinary fits](expanded_peak_diagnostic.json)
instead of two still recovered neither. This separates the signal being present
at its known ephemeris from the search successfully finding it; it does not
establish a new planet or prove the precise cause of the misses.
