# Research status: 2026-09-07

**Initial campaign complete. No surviving planet candidate, new planet or
demonstrated methodological breakthrough.**

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
unflagged trial fits in the completed campaign, with source hashes and evidence.
These variants overlap: 1,031 distinct stars have had a period search, including
the known-host check. Periodic filtering has finished for all 992 usable main
targets, with no unflagged fits. The combined-season pass has also finished:
908 targets supported its stricter sector split and yielded 1,816 trial fits;
84 were skipped for insufficient sectors. Its only unflagged fit was the
already reviewed Wolf 1069 alias.

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

Twenty-six offline numerical checks pass, including a test that changing final-holdout
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

Downloads and all configured search passes are complete. The final
[result audit](result_audit.json) passed with 4,023 result files, no failed
consistency checks, no pending execution stages and no unreviewed unflagged fits.
It covers main results plus specified controls and diagnostics, so its file count
is not a star count. The [input audit](input_audit.json) recorded 7,513 FITS files
with no target-identity or time-reference failures. These audits establish
artifact consistency, not astrophysical validity or comprehensive sensitivity.

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

A [further ten-target review](vetting/relaxed_second_tranche_review.json) of
stronger second-tranche signals passing non-physical gates also promoted none.
The deepest eclipse is in the already studied binary TIC 142979644. Separately,
the known-host residual review identifies [RR Cae's binary eclipses](vetting/219244444/disposition.json)
as a long-period alias; it does not reassess the catalogue's circumbinary companion.

The [final combined-season review](vetting/relaxed_final_combined_review.json)
examined seven additional trial fits on six targets. None was promoted. In
TIC 378527773, dimming repeats in all 14 and all 16 subdivisions of the two
trial periods, in both training and held sectors, supporting a shorter-period
variability interpretation. Source identity and variability type remain unclassified.

A subsequent [pixel-origin diagnostic](vetting/relaxed_final_combined/378527773_short_cycle_pixels/disposition.json)
places TIC 378527773's roughly nine-hour difference signal about 1.45 and 1.33
pixels from the target in sectors 17 and 58. The approximate sky positions agree
within 3.8 arcseconds. This supports a nearby source of the variability; it does
not identify that source or establish a planet. Source-specific extraction is
being investigated as a separate development direction.

The [accelerated execution benchmark](../docs/PERFORMANCE.md) preserves all
scientific outputs on three tested real inputs and reduces their aggregate wall
time by about 44%. The remaining 307 combined-season result files were completed
with that adapter. [The integrity check](performance/checkpoint_integrity.json)
confirms that all 685 earlier completed files remained byte-for-byte unchanged
and all 307 adapter records match the saved code hashes.

A separate [method-invention experiment](experiments/cross_view/FINDINGS.md)
tested frozen predictions of the dimming source across observing geometries.
It has not demonstrated sufficient benefit over the same spatial filter with
independent localization, so it has not been adopted. Its protocol, negative
ablation result and complete trial scores are preserved. An
[uncertainty-weighted variant](experiments/cross_view_uncertainty/FINDINGS.md)
gained six target recoveries but accepted seven more displaced injections than
the stronger comparison across 1,800 simulated cases on real difference maps.
A [pixel-extraction prototype](experiments/protected_pixels/FINDINGS.md) preserved
its modeled target response but increased short-timescale noise in all eight
reserved sector halves. Neither variant met the quality requirement or was adopted.

Two subsequent [baseline-feasible](experiments/relative_pixels/FINDINGS.md) and
[transit-timescale](experiments/multiscale_pixels/FINDINGS.md) revisions reduced
rapid scatter in every development sector. The latter limited the worst reserved
two-hour scatter increase to 4.4%, but its median improvement remained below the
predeclared 10% gate. Both failed their full development gates and remain unused
by the production search. These small noise experiments are not planet recoveries.

An additional [cycle-excluded variability experiment](experiments/cycle_excluded/FINDINGS.md)
completed 90 paired runs. Its median-template filter recovered six of 27 faint
synthetic cases under strict checks, versus five for each harmonic comparison,
with no lost comparison recoveries. It nevertheless missed the predeclared gate
of two additional recoveries. All three methods produced one unflagged fit on
the three unmodified-star diagnostics. This is a development result, not a new
planet, calibrated false-alarm rate or sufficient basis for adoption.

A fresh [three-pass comparison](experiments/multimode_cycles/FINDINGS.md) completed
another 90 runs with identical mode budgets. The cycle-excluded method recovered
six strict cases versus seven for the stronger harmonic comparison and lost one
of its recoveries. All three filters removed the previously unflagged fit in the
unmodified-star diagnostics. The new variant failed its gate and remains unused.

Two source-specific pixel experiments also failed. [Static periodic-source
suppression](experiments/periodic_source/FINDINGS.md) reduced the modeled periodic
component by about 14%, with insufficient improvement over the stronger pixel
comparisons. A [spatially protected temporal reference](experiments/protected_reference/FINDINGS.md)
preserved at least 99.7% of depth in the fresh finite-model tests, but improved
median two-hour scatter by only about 4% and underperformed direct harmonic
subtraction. Neither was applied to the four additional pixel views or adopted.

A [search-bottleneck diagnostic](experiments/search_bottleneck/FINDINGS.md)
shows that broad, physically implausible seed fits can crowd out measurable
synthetic transits. The subsequent [150-run duration-prior experiment](experiments/physical_duration/FINDINGS.md)
recovered 20 of 45 injections under strict checks, tying the stronger comparison
and losing one of its strict recoveries. It failed the development gate. Its
[prepared six-star physical-transit assessment](experiments/realistic_duration/FINDINGS.md)
remains unexecuted. The two selected diagnostic cases did not establish a
population-level gain.

An [early-training-qualification ablation](experiments/qualified_seeds/FINDINGS.md)
completed another 100 runs and reused 100 exact reference runs. The complete
revision retained 22/45 strict injected recoveries, compared with 19 for the
original, 20 for stronger harmonic cleaning, and 21 for its simpler revision.
It lost none of those comparisons' strict recoveries and added no unflagged
unmodified-star fit, but failed its incremental gain-of-two gate. A
[separately frozen confirmation experiment](experiments/pipeline_confirmation/FINDINGS.md)
then completed all 240 runs on six other stars with physical transit models.
The simpler revision recovers 7/54 strictly, the qualified revision 6/54, and
both legacy pipelines 4/54. Neither revision loses a legacy strict recovery;
both pass the complete-pipeline criteria, with the simpler revision selected
by the frozen rule. Absolute sensitivity remains low, and this small shared-star
sample cannot establish survey completeness. The earlier gate remains failed
and the earlier 180-run assessment remains unexecuted.

A [real-signal control](calibration/revised_pipeline/FINDINGS.md) finds that both
revisions preserve the known 37.424-day TOI-700 planet under strict checks; neither
recovers the known 27.810-day signal among its two fits. A [100-star pilot selection](../provenance/revised_pilot_selection.json)
is frozen using only catalogue properties and observation counts. Both conditions
now pass, allowing [the fixed revision's exploratory execution](../docs/REVISED_PILOT_EXECUTION.md).
It reanalyses existing targets and does not add to the distinct-star count.

The [100-star pilot is now complete](revised_pilot/STATUS.md): all 200 trial fits
fail the held-sector evidence requirement, with zero execution errors and no
planet candidate. Long-duration flags fall from 200 to 11 on the same 100 stars,
but nominal training-SNR failures increase from 29 to 84 and no fit passes all
checks. The [final pilot audit](revised_pilot/audit.json) verifies every input and
receipt; all fits, including per-event measurements, are exported. A separate
[known-timing diagnostic](experiments/confirmation_diagnostic/FINDINGS.md) shows
both weak event SNRs and missed period selections in the physical-injection
sample. It did not change the pilot or any completed experiment's criteria.

The initial data campaign is complete; method development continues as separate,
bounded experiments. A non-detection does not establish that these systems lack
planets. Adopting another method requires a measurable advantage and independent
validation. The completed campaign does not justify a discovery claim.
