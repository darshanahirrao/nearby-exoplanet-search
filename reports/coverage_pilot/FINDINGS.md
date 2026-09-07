# Twenty-star coverage pilot: complete, no surviving trial

All 20 selected stars finished processing, with zero download or execution
errors. The search retained 39 trial fits; **all 39 fail the held-sector
recurrence screen, and none passes all screening checks.** No planet candidate
or discovery is established.

| Measure | Completed result |
| --- | ---: |
| Previously searched stars reanalysed | 20 |
| Original sector products | 360 |
| Additional sector products downloaded | 390 |
| Selected products usable after processing | 750 / 750 |
| Retained trial fits | 39 |
| Fits passing every screening check | 0 |
| Artifact audit checks / failures | 3,561 / 0 |

The maximum of two retained fits per star is a cap. One star stopped after one
fit under the unchanged weak-signal stopping rule. [Every retained fit](trials.json),
including its event measurements and rejection flags, is disclosed. Flag counts
in the [summary](summary.json) overlap and must not be added as unique fits.

The [selection plan](plan.json) and executable code were
[published before download](https://github.com/darshanahirrao/nearby-exoplanet-search/commit/6f08d259dc6fd966559a7394f0500aa15730e99a).
They fix the first 20 ranked stars in the published unused-coverage inventory.
Selection used prior archive metadata and previously examined flux; none of the
390 added products had been downloaded for this selection.

The [protocol](../../docs/COVERAGE_PILOT.md) uses the unchanged `coarse_only`
revision, whose prior complete-pipeline comparison and known TOI-700 d control
passed. Original light-curve files and completed results are preserved. No
screening threshold or failed experimental adoption gate was changed.

The [audit](audit.json) checks all 750 input hashes and target/sector identities,
separation of old and added timestamps, agreement with the publicly frozen plan,
download/search chronology, output receipts, frozen trial parameters, distinct
training and held sectors, and event-score arithmetic. Exact archive products
and downloaded hashes are in the [download manifest](download_manifest.json);
the [execution plan](execution_plan.json) and [completed run](results.json)
record the remaining provenance. The audit can be repeated locally with
`python scripts/export_coverage_pilot.py` after restoring the recorded inputs
and outputs.

These checks establish artifact consistency, not astrophysical validation or
calibrated false-alarm probabilities. This exploratory reanalysis does not
measure survey completeness or rule out planets around these stars. The
distinct-star count remains **1,031**. The other 45 stars subsequently
[completed the coverage continuation](../coverage_continuation/FINDINGS.md).
