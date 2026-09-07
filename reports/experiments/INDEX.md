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
| [Complete-pipeline confirmation](../../docs/EXPERIMENT_PIPELINE_CONFIRMATION.md) | Separately frozen 240-run comparison of four unchanged pipelines on six other stars and physical transit models. | Outputs in progress; no result yet |

Each completed experiment links to its findings, exact plan, code hashes and
outcomes. The original production results remain unchanged. No methodological
priority or breakthrough has been established.

For a compact local snapshot, run:

```sh
python scripts/progress.py --experiments-only
```

This reports output-file state, including prepared and partial work. A partial
file alone does not prove that a numerical process is still running.
