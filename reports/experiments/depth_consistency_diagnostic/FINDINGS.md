# Depth-scatter penalty did not resolve the selected misses

All 384 first-iteration fine fits were reconstructed. Their fitted durations,
nominal BLS SNRs, combined local SNRs and leave-one-event-out scores matched the
saved values within the declared numerical tolerances. Only previously eligible
training fits entered the following ranking comparison.

| Exposed case | Original leave-one-event-out rank | Rank after depth-scatter inflation |
| --- | ---: | ---: |
| TIC 233738219, orbit 2, one Earth radius | 10 | 6 |
| TIC 229614158, orbit 0, one Earth radius | 18 | 25 |
| TIC 328799321 control | 1 | 1 |

The penalty improves one miss and worsens the other; neither enters the first
two positions. It was not adopted or sent to a larger recovery experiment.
These ranks are within eligible fine fits, a different list from the earlier
4,096-coarse-seed diagnostic. They must not be combined into a single rank-change
percentage.

The calculation divides each ranking score by `sqrt(max(1,Q))`, where `Q` is
the reduced weighted scatter around a common event depth. It never reduces the
nominal error scale. Shared baseline windows and residual variability prevent
interpreting this as a calibrated chi-square test or false-alarm probability.

See the [protocol](../../../docs/DIAGNOSTIC_DEPTH_CONSISTENCY.md), [manifest](plan.json),
[summary](results.json), and individual case files for every reconstruction.
This is exposed development evidence, not blind recovery or a discovery.
