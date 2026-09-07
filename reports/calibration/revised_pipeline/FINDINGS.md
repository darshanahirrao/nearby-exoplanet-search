# Real-signal regression control

All four complete pipelines recover the previously known TOI-700 d signal under
strict training/held-sector checks and every astrophysical screening check.
None retains TOI-700 e among its two fitted signals. The revisions preserve this
control's established recovery; they do not demonstrate an additional real-planet
recovery here and are not new discoveries.

| Method | Recovered period (days) | Nominal training SNR | Held-sector SNR | Known 27.810-day signal retained? |
| --- | ---: | ---: | ---: | --- |
| Original single-pass search | 37.423396 | 14.792 | 10.116 | No |
| Three-pass harmonic comparison | 37.423396 | 14.562 | 10.116 | No |
| Physical coarse seeds, original fine fit | 37.423316 | 14.398 | 9.601 | No |
| Same, with early training qualification | 37.423316 | 14.398 | 9.601 | No |

Both revisions retain strict recovery while yielding slightly smaller nominal
scores on this signal. They are not universally superior. Every method also
selects a roughly 68.57-day fit which fails the held-sector checks.

The original pipeline's blind signal fields exactly reproduce the previous
corrected control. The remaining JSON differences are documented catalogue
annotations and a subsequently added config field for the two-fit budget.
All training ephemerides agree exactly with their records frozen before holdout.
See the [audit](audit.json), [plan](plan.json), [compact results](results.json)
and [protocol](../../../docs/CALIBRATION_REVISED_PIPELINE.md).

This 37-sector input and its planets were inspected previously. It is a known-
signal regression control, not independent target selection or a sensitivity
survey. The numerical timings were measured while another experiment was running,
with one BLS thread per call; they are not a controlled speed benchmark.

The planets were already reported by the TESS team: [TOI-700 d](https://www.nasa.gov/universe/nasa-planet-hunter-finds-its-1st-earth-size-habitable-zone-world/)
and [TOI-700 e](https://www.nasa.gov/universe/nasas-tess-discovers-planetary-systems-second-earth-size-world/).
Habitability is not established by these light curves or an irradiation estimate.

After recreating the corrected TOI-700 input from the README, run
`python scripts/pipeline_control.py`. Exact replay requires the saved catalogue
and telescope inputs, not a later archive snapshot.
