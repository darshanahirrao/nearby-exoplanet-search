# Method experiments

The original campaign searched 1,031 distinct stars and produced no surviving
planet candidate. The experiments below investigate limitations of that search.
They are not astrophysical discoveries. Different rows use different samples and
metrics; their scores cannot be combined into a survey completeness estimate.

| Experiment | Main finding or current state | Decision |
| --- | --- | --- |
| [Cross-view source prediction](cross_view/FINDINGS.md) | Most benefit came from the spatial filter; freezing the position added too little over the stronger comparison. | Not adopted |
| [Source-position uncertainty](cross_view_uncertainty/FINDINGS.md) | More target recoveries came with more accepted displaced-source signals. | Quality gate failed |
| [Absolute response constraints](protected_pixels/FINDINGS.md) | Modeled target response was protected, but rapid noise increased in all eight tested views. | Gate failed |
| [Relative response and noise caps](relative_pixels/FINDINGS.md) | Rapid noise improved; reserved two-hour behavior failed the full gate. | Gate failed |
| [Multiple transit timescales](multiscale_pixels/FINDINGS.md) | Median two-hour gain remained below the required 10%. | Gate failed |
| [Cycle-excluded variability](cycle_excluded/FINDINGS.md) | 6/27 strict injected recoveries versus 5/27 for the comparisons; required gain was two. | Gate failed |
| [Equal three-pass variability comparison](multimode_cycles/FINDINGS.md) | 6/27 strict recoveries versus 7/27 for the stronger comparison, with a lost recovery. | Gate failed |
| [Static periodic-source suppression](periodic_source/FINDINGS.md) | Too little periodic/noise improvement over the stronger pixel comparisons. | Gate failed |
| [Protected periodic reference](protected_reference/FINDINGS.md) | At least 99.7% modeled depth response in fresh finite-family tests, but only about 4% median two-hour noise improvement. | Gate failed |
| [Search-bottleneck diagnostic](search_bottleneck/FINDINGS.md) | Broad seed fits can crowd out detectable synthetic transits before physical vetting. | Selected-case diagnostic |
| [Early duration prior](physical_duration/FINDINGS.md) | 20/45 strict recoveries, tying the stronger comparison and losing one strict recovery. | Gate failed |
| [Physical-transit follow-up](realistic_duration/FINDINGS.md) | 180 method runs were prepared on six other stars; none executed because the prerequisite failed. | Remains unused |
| [Early training qualification](qualified_seeds/FINDINGS.md) | 22/45 strict recoveries versus 19 for the original and 21 for the strongest simpler revision; no lost strict recovery. | Incremental-gain gate failed; independent comparison needed |
| [Complete-pipeline confirmation](pipeline_confirmation/FINDINGS.md) | 240 runs: simpler revision 7/54 strict recoveries, qualified revision 6/54, both legacy pipelines 4/54; no lost legacy recovery. | Both pass; simpler revision selected for pilot |
| [Known-timing sensitivity diagnostic](confirmation_diagnostic/FINDINGS.md) | 11/54 cases meet reference event SNRs when given their true timing; five of those are not strict blind recoveries. | Retrospective diagnostic; no changed gates |
| [Real TOI-700 control](../calibration/revised_pipeline/FINDINGS.md) | All four methods recover the known 37.424-day planet strictly; none retains the known 27.810-day signal. | Existing real recovery preserved |
| [Conditional 100-star pilot](../revised_pilot/STATUS.md) | 100/100 finished; 200 trial fits; none passes held-sector checks. All inputs and receipts audited. | No candidate; all fits exported |
| [Repeated-event coarse ranking](period_rank_diagnostic/FINDINGS.md) | Two exposed injection ranks improve from 1,316/2,108 to 84/76; the control remains first. | Selected-case diagnostic only |
| [Two-fit repeated-event search](repeated_events/FINDINGS.md) | Six initial runs preserve the control but recover neither missed injection. | Smoke guard failed; 114 planned runs unused |
| [Depth-consistency penalty](depth_consistency_diagnostic/FINDINGS.md) | Within eligible fine fits, one truth rank improves from 10 to 6; the other worsens from 18 to 25. | Not adopted |
| [Larger candidate shortlist](portfolio/FINDINGS.md) | All 120 new runs complete; strict recoveries 9/54 versus 7/54 for the reference, but extra unmodified fits require vetting. | Both adoption gates failed; no fresh assessment selected |

Each completed experiment links to its findings, exact plan, code hashes and
outcomes. The original production results remain unchanged. No methodological
priority or breakthrough has been established.

For a compact local snapshot, run:

```sh
python scripts/progress.py --experiments-only
```

This reports output-file state, including prepared and partial work. A partial
file alone does not prove that a numerical process is still running.
