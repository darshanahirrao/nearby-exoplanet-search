# Research status: 2026-09-07

**No newly discovered or validated planet. The search continues.**

All 1,000 selected targets have finished downloading and initial processing:
992 targets supplied at least two sectors; eight had fewer. All 992 processed
targets supported the configured period search. We retained 3,586 initial trial
fits, including weak and rejected fits. These are not 3,586 planet candidates.

The timing-refined screen produced eight unflagged trial periods on five stars.
All show hour-scale variability aliases and have been rejected as evidence for temperate
planets. Origin of the variable flux is not localized; these checks do not rule
out other planets in either system.

| Target | Trial period | Short variation | Disposition |
| --- | --- | --- | --- |
| TIC 352617553 / Wolf 1069 | 8.1883 days | About 2.656 hours; roughly 74 cycles per trial period | [Rejected alias and diagnostics](vetting/352617553/disposition.json) |
| TIC 328463799 | 4.9773 days | About 2.655 hours; roughly 45 cycles per trial period | [Rejected alias and diagnostics](vetting/328463799/disposition.json) |
| TIC 138579249 | 7.0533 days | About 5.644 hours; roughly 30 cycles | [Rejected alias and diagnostics](vetting/138579249/disposition.json) |
| TIC 256771035 | 14.8602, 9.1373 and 9.9068 days | About 6.256 hours; roughly 57, 35 and 38 cycles | [Rejected aliases and diagnostics](vetting/256771035/disposition.json) |
| TIC 441606549 | 8.9710 and 10.4661 days | About 4.485 hours; roughly 48 and 56 cycles | [Rejected aliases and diagnostics](vetting/441606549/disposition.json) |

The four initially unflagged fits were also reviewed and rejected. A separate
51-host search for additional planets has finished; its only unflagged trial is
another variability alias in Wolf 1069. The combined-season pass found the same
alias. [The explicit review ledger](vetting/unflagged_review.json) records all 14
unflagged trial fits reviewed at this checkpoint, with source hashes and evidence.
These variants overlap: 1,031 distinct stars have had a period search, including
the known-host check. The remaining filtering and combined-season scans continue.

## Calibration and verification

The known TOI-700 d signal was recovered near **37.42362 days**, with nominal
signal-to-noise about **11.8** in the final held-back observations. Discovery,
timing-refinement and final holdout data have distinct roles. This is a known-planet
calibration, not a new discovery.

| Experiment | Synthetic cases | Recovered by configured search | Also passed strict holdout check |
| --- | --- | --- | --- |
| Initial pilot | 27 | 17 | 8 |
| Fresh timing-refined suite | 27 | 18 | 13 |
| Periodic filtering, same cases as timing-refined suite | 27 | 22 | 17 |
| Periodic filtering, fresh cases | 27 | 23 | 23 |
| Combined seasons with periodic filtering, fresh cases | 27 | 23 | 23 |

Only the explicitly paired suites use identical periods and phases; the other
suites use different deterministic plans on the same three selected stars.
Combined-season trials retain two peaks; the other suites retain three. These
counts cannot be interpreted as a controlled comparison across all rows. Trials inject
0.8, 1.0 and 1.5 Earth-radius box signals before our binning/detrending. Box shapes
favor the BLS search and do not include upstream SPOC signal losses. This small
sample does not establish survey completeness or false-positive probabilities.
The faint, variable control TIC 232970271 yielded no recovered injections in the
first two suites. Periodic filtering improves this limited sensitivity check;
non-detections still cannot exclude small planets.

Eight offline numerical checks pass, including a test that changing final-holdout
flux leaves the fitted ephemeris unchanged while reversing the measured holdout
signal. Local execution, code, data-product references and failure records are
retained for independent inspection.

## Reproduce or inspect

- [Target processing table](tables/targets.csv)
- [Initial trial fits and flags](tables/initial_screening.csv)
- [Refined trial fits, final holdout and vetting notes](tables/refined_screening.csv)
- [Machine-readable summary](summary.json)
- [Exact observation products and hashes](../provenance/observations.json)
- [Initial injection plan](calibration/injections/plan.json) and [recovery results](calibration/injections/recovery.csv)
- [Fresh injection plan](calibration/injections_refined_fresh/plan.json) and [recovery results](calibration/injections_refined_fresh/recovery.csv)
- [Known-planet calibration](calibration/150428135_calibration_v2_refined.json)

Downloads, first-pass screening and timing refinement are complete. The tables
and machine summary remain checkpoints while the final variability-filtered and
combined-season searches finish. [The result audit](result_audit.json) checks
frozen ephemerides, available source hashes and outstanding execution coverage.

The combined-season control recovers known TOI-700 d near 37.42340 days, with
nominal held-sector S/N 10.1. It does not recover known TOI-700 e among its two
retained peaks, although a catalogue-ephemeris diagnostic shows a weak signal.
This explicitly demonstrates incomplete sensitivity. A diagnostic review of 15
additional targets relaxed the approximate physical cuts. One sharper signal,
TIC 448416124, localizes away from the intended target in three sectors:
[pixel evidence and disposition](vetting/448416124/disposition.json). The other
folds show broad variability or lack a compelling isolated transit. None has
been established as a new planet; [review notes](vetting/relaxed_variability_review.json)
preserve the individual assessments.

A further [five-target combined-season review](vetting/relaxed_combined_review.json)
also produced no promoted candidate. A sharp dip in TIC 408232559 localizes away
from the intended star in three sectors. A 5.298-day trial in TIC 282923395 instead
shows dimming in all six subdivisions of that period, consistent with a shorter
variability alias. Source identity, variability type and novelty are not established.

Pixel localization, full astrophysical validation and new observations would be required
for any serious surviving candidate. HZ irradiation alone does not establish water,
habitability or life.
