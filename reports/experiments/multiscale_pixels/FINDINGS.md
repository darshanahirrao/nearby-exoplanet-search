# Transit-timescale objective reduced regressions but missed the gain gate

All eight optimizations completed without fallback. Seven reserved halves had lower compensated two-hour scatter; the eighth increased by 4.4%, within the predeclared 5% tolerance. Rapid scatter decreased in all eight. However, the median two-hour ratio was 0.952, failing the required maximum of 0.900. The complete development gate failed; this revision is not adopted and does not justify a fresh-data follow-up under this protocol.

| TIC | Sector | Rapid scatter ratio | Two-hour scatter ratio |
| --- | ---: | ---: | ---: |
| 448416124 | 9 | 0.937 | 0.810 |
| 448416124 | 36 | 0.950 | 0.927 |
| 448416124 | 63 | 0.903 | 0.986 |
| 408232559 | 5 | 0.869 | 0.817 |
| 408232559 | 32 | 0.948 | 0.977 |
| 408232559 | 6 | 0.897 | 0.988 |
| 282923395 | 14 | 0.967 | 1.044 |
| 282923395 | 48 | 0.960 | 0.887 |

The lowest in-range random relative target response was 1.000222. The mathematical constraints cover modeled footprints and training covariance estimates. They do not establish preservation for unknown real point-spread functions, nor do these scatter metrics establish planet recovery.

The compensation exactly removes a constant. It removes a linear time trend when neighboring bins have symmetric effective observing times; partial coverage can break that symmetry. The current implementation requires at least half-bin coverage but does not correct this timing asymmetry. Results must not be interpreted as an exact trend-annihilation guarantee for arbitrary gaps.

The eight sectors were reused after inspection in earlier experiments. This is method development, not independent validation. Minimax constrained estimation is established mathematics; no invention priority is claimed.

- [Frozen protocol](../../../docs/EXPERIMENT_MULTISCALE_PIXELS.md)
- [Frozen plan](plan.json)
- [Measurements and response draws](results.json)
- [Code](../../../scripts/multiscale_pixel_experiment.py)

Reproduce with `python scripts/multiscale_pixel_experiment.py` after preparing the existing cross-view inputs.
