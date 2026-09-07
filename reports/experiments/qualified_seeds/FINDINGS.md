# Earlier training qualification: incremental gate missed

All 100 new runs completed without errors. The comparison reuses 100 frozen
reference runs on exactly the same 45 injected cases and five unmodified stars.
This is retrospective development, not independent validation.

| Method | Period recovered / 45 | Strict recovery / 45 | Strict and all screening checks | Unflagged unmodified-star fits |
| --- | ---: | ---: | ---: | ---: |
| Original search | 24 | 19 | 19 | 1 |
| Three-pass lower-threshold harmonic cleaning | 25 | 20 | 20 | 0 |
| Physical coarse seeds; original fine fit | 26 | 21 | 21 | 0 |
| Same, with early training qualification | 28 | 22 | 22 | 0 |

No strict recovery from any comparison was lost. Early qualification gained
one strict recovery over the strongest simpler revision, below the predeclared
gain of two. Its development gate therefore **failed**. The original production
search has not been replaced, and no methodological novelty is established.

The complete revision gained three strict recoveries over the original pipeline
and two over its stronger harmonic comparison on these reused cases. This is a
promising development observation, not proof of generalization. The distinction
between the combined gain and the failed incremental-component gate matters.

An independently checked unit fixture confirms that changing held-sector flux
does not change the qualified training period, epoch or duration; it reverses
the held-sector signal instead. This checks information flow, not astronomical
validity. Inspecting more training peaks increases computation and does not
provide a calibrated search false-alarm probability.

The next research question is whether either complete revision generalizes to
other stars and physical transit shapes. That requires a separately frozen
comparison with both revisions and both legacy baselines. It does not change
this failed gate or activate the earlier unused duration-only assessment.

See [frozen plan](plan.json), [all outcomes](results.json), and
[protocol](../../../docs/EXPERIMENT_QUALIFIED_SEEDS.md). Reproduce with
`python scripts/qualified_seed_experiment.py --workers 3` after reproducing its
explicitly referenced comparisons. All 64-per-slot training refinements and
rejections are stored in each local `frozen_training.json`; at most two fits
reach the unchanged held-sector checks.
