# Retrospective sensitivity check on the fresh observations

Four fixed-timing injections are measurable after processing the same 21
sectors in which the two unmodified trials failed recurrence. This supports
rejecting those specific trial fits, rather than treating the absence of a
fresh signal as an automatic consequence of the processing.

The [plan](plan.json) was specified after the fresh-sector non-detection and
before running these injections. For each trial it uses the originally fitted
box depth and duration, or a circular central transit of the original estimated
radius (0.7902 and 0.8863 Earth radii). The physical model has quadratic limb
darkening [0.3, 0.2], seven-point 120-second exposure integration, and durations
of 0.09230 and 0.10222 days. The larger original fitted windows remain in use
for measurement, with no timing or duration optimization.

The nominal original/quadratic scores are 10.29/9.35 and 7.23/6.74 for the
primary box and physical controls, and 12.72/8.79 and 8.45/5.12 for the
comparison controls. All retain at least three events, at least 60% positive
event depths and scores of at least 5 in both statistics. All four inputs and
outcomes are disclosed in [the results](results.json).

These are selected deterministic models on already examined observations,
not blind recoveries, additional real signals, a completeness measurement or
planet validation. Injection precedes this project's detrending and harmonic
processing but does not reproduce possible upstream SPOC processing losses.
The controls do not change the frozen follow-up or any earlier experiment.

Reproduce with `python scripts/check_fresh_followup_injections.py`.
