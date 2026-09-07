# Repeated-event ranking: development protocol

The selected-case diagnostic moves two missed injected transits from global
ranks 1,316 and 2,108 to leave-one-event-out ranks 84 and 76. It preserves one
positive control at rank one. These exposed results motivate a 128-model fine
budget; that budget is a development choice informed by the examples, not an
independently discovered physical constant. No blind recovery is established
by a rank change alone.

Use the same 54 exposed physical injections on six stars plus six unmodified
diagnostics from `pipeline_confirmation`. Compare two new fixed revisions:
local total event SNR and the minimum SNR after any one event is omitted, capped
at the full SNR. Both use the same 4,096 distinct physical-duration coarse peaks,
local baseline definition, minimum three sampled events and 128 refinements per
retained signal. Each refines the highest-ranked 128 with the original 301-period
grid and original duration family. Apply all original training checks, then
choose the highest-ranked eligible fine fit. Mask it using the unchanged rule,
repeat for at most two retained fits, freeze the training record, and apply all
original held-sector checks unchanged. Record every refinement and rejection.

Before the full comparison, run the three diagnostic injections with both
revisions, yielding six smoke runs. Permit the full comparison only if at least
one revision preserves the known recovered injection under all checks and
recovers at least one of the two prior misses under all checks, without smoke
execution errors for that revision. If this guard fails, preserve the six
results and leave the remaining planned runs unused. This saves compute; it is
not an adoption gate or independent validation.

If permitted, complete all 120 planned runs, reusing those six exact results.
Compare against the 120 exact prior `coarse_only` and `qualified_seeds` reference
results. For each new revision require at least two more strict recoveries than
the stronger reference, no lost strict recovery from either reference, at least
as many all-screening recoveries as either reference, no additional unflagged
unmodified-star fit, gains on at least two stars, and no execution errors.
If both pass, choose more all-screening recoveries, then more strict recoveries,
then the simpler local-total statistic. The two new rankings are also a direct
comparison at equal budgets; report both even if only one qualifies.

This is development on previously exposed cases. A passing revision still
requires physical injections on other stars and preservation of the real
TOI-700 d control before another real-data search. Do not change the completed
100-star pilot, prior gates, source code or held-sector thresholds.

The local errors are nominal and baseline windows can overlap. Ranking scores
are not calibrated significance or false-alarm probabilities. Event consistency
has substantial [prior art in Kepler](https://arxiv.org/abs/1302.7029); this is
an unvalidated project hypothesis, not established novelty or a planet discovery.
