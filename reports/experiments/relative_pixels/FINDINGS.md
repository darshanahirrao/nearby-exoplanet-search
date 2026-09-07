# Noise caps improved rapid scatter but missed the transit-timescale gate

The baseline-feasible revision reduced adjacent-difference scatter in all eight reserved sector halves by 3.0–14.5%. Its median compensated two-hour scatter ratio was 0.970, short of the preregistered maximum of 0.900. Two sectors exceeded the allowed 1.050 ratio. The development gate therefore failed; this version is not adopted and does not justify an independent-data follow-up.

All eight optimizations completed without fallback. The smallest relative response among the in-range random footprints was 0.999479. Modeled noise constraints govern the training covariances, not actual held-sector noise.

| TIC | Sector | Rapid scatter ratio | Two-hour scatter ratio |
| --- | ---: | ---: | ---: |
| 448416124 | 9 | 0.970 | 0.850 |
| 448416124 | 36 | 0.939 | 1.032 |
| 448416124 | 63 | 0.909 | 0.978 |
| 408232559 | 5 | 0.855 | 0.811 |
| 408232559 | 32 | 0.966 | 0.962 |
| 408232559 | 6 | 0.889 | 1.067 |
| 282923395 | 14 | 0.955 | 1.106 |
| 282923395 | 48 | 0.925 | 0.853 |

Lower ratios are better. These are noise statistics in normalized extraction units, not end-to-end planet recovery rates. The sectors were inspected in earlier experiments, so this is development data. A separate synthetic unit check verifies suppression of a contaminating spatial source and preservation of an injected target transit on independent random samples.

- [Frozen protocol](../../../docs/EXPERIMENT_RELATIVE_PIXELS.md)
- [Frozen plan](plan.json)
- [All measurements](results.json)
- [Code](../../../scripts/relative_pixel_experiment.py)

Reproduce with `python scripts/relative_pixel_experiment.py` after preparing the existing cross-view inputs.
