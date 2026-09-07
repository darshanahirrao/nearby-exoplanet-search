# Larger candidate shortlist: comparison complete, adoption gates failed

**Follow-up outcome:** both additional unmodified fits
[fail recurrence in 21 previously unused sectors](../../vetting/fresh_sector_followup/FINDINGS.md).
Retrospective injections remain measurable there. Neither trial is retained
as a credible periodic planet lead; the original adoption gates stay failed.

All 120 new development runs completed without errors, with 60 exact reference
runs reused. Each method was assessed on 54 physical injections and six
unmodified-star controls. The six initial runs passed the smoke condition for
the leave-one-event-out shortlist and were included in the final comparison.

| Method | Strict recoveries | Recoveries passing every screening check | Unmodified controls with an unflagged fit |
| --- | ---: | ---: | ---: |
| Coarse-only reference | 7/54 | 7/54 | 0/6 |
| Local-total shortlist | 7/54 | 7/54 | 1/6 |
| Leave-one-event-out shortlist | 9/54 | 9/54 | 1/6 |

Neither revision loses a reference strict recovery. The two additional strict
recoveries belong to the previously examined misses on TIC 233738219 and
TIC 229614158. Both revisions nevertheless **fail their predeclared adoption
gates** because each produces an additional unflagged fit in an unmodified
control. No method is selected for fresh assessment.

This is exposed development data, not an independent confirmation of the gains.
Both unmodified fits are on TIC 233738219: 26.316459 days for leave-one-event-out
and 35.394150 days for local-total. Unmodified observations are not certified
planet-free; the extra fits are **unverified**, not established false alarms or
new planets. They are preserved in the [review queue](unmodified_review_queue.json).
A [fixed-timing diagnostic](../../vetting/portfolio_extra_fits/FINDINGS.md)
shows weaker SAP support and inconclusive profiles. Source localization and
stellar-variability checks are still needed. A subsequent
[rotation and individual-event review](../../vetting/portfolio_rotation/FINDINGS.md)
finds substantial variability and local-baseline concerns but does not resolve
the residual fits. The failed gate does not justify
expanding a survey with either revision.

Both methods retain at most 32 eligible fits from one 128-refinement training
pass. Lower-ranked fits sharing over half of the smaller set of in-transit
training samples are removed. A separate software fixture verifies retention
of three strong injected planets and independence from held-sector flux. The
overlap rule can merge coincident commensurate signals and needs sensitivity
assessment.

The [protocol](../../../docs/EXPERIMENT_PORTFOLIO.md), [plan](plan.json),
[six initial outcomes](smoke_results.json) and [complete results](results.json)
preserve the comparison. The [artifact audit](audit.json) passes 3,498 checks
with zero failures, including frozen training parameters, input hashes, sector
separation and outcome accounting. It does not establish astrophysical validity
or a calibrated false-alarm rate. All earlier failed gates and the completed
100-star pilot remain unchanged. No method novelty or breakthrough is established.
