# Candidate-capacity experiment

The two-fit repeated-event smoke test failed and its remaining 114 planned
runs remain unused. Both missed injected periods can appear among eligible
fine fits but lose the two retained slots. A depth-scatter penalty did not
solve this: it improved one truth rank from 10 to 6 but worsened the other
from 18 to 25. That penalty is not adopted.

This new development experiment explicitly changes the retained-fit budget.
From one unchanged 128-refinement pass, retain at most 32 distinct eligible
training fits, ranked either by local total SNR or leave-one-event-out SNR.
Use the same 4,096 coarse-seed budget and original fine-fit family for both.
Remove a lower-ranked fit if its transit windows share more than half of the
smaller set of in-transit training samples with a retained fit. A three-planet
software fixture exposed that period-distance deduplication alone retained
multiple wings and harmonics of one signal, crowding out other strong signals;
this sample-overlap rule is fixed before running the astrophysical experiment.
It can merge commensurate signals with coincident events, a stated limitation.
Do not mask observations or run another refinement pass. Freeze every selected
ephemeris before evaluating any held-sector evidence. Keep every original
physical and held-sector screening threshold unchanged. The larger trial count
requires its own sensitivity and unmodified-star comparison; fixed SNR cuts
alone do not control global false-alarm probability.

The choice of 32 is informed by exposed training ranks and is a development
choice. Run the same three smoke injections with both equal-budget rankings.
Allow the complete comparison only if at least one revision retains the known
recovered injection under all checks and recovers at least one missed injection
under all checks without smoke errors for that revision. Otherwise stop and
preserve the guard failure.

If permitted, complete the same 54 physical injections and six unmodified stars
for both rankings: 120 new runs including the six cached smoke runs. Reuse the
60 exact `coarse_only` references. For each revision require at least two extra
strict recoveries, no lost reference strict recovery, at least as many
all-screening recoveries, no additional unflagged unmodified-star fit, gains
on at least two stars, and no execution errors. Compare the two rankings at
equal budgets. Select more all-screening recoveries, then more strict recoveries,
then the simpler local-total ranking if tied. Do not attribute a capacity gain
to the leave-one-out statistic without support from this equal-budget comparison.

A development pass requires a fresh-star assessment and preservation of real
TOI-700 d before a further real-data search. Preserve all preceding failures,
the completed 100-star pilot, and every trial in this experiment. This is not
a discovery, calibrated false-alarm rate, independent assessment or established
methodological novelty.
