# Equal multi-mode budgets did not favor the cycle-excluded filter

All 90 runs completed without errors: 27 new faint injections and three unmodified-star diagnostics, each processed by three filters with at most three variability passes.

| Three-pass filter | Recovered injections | Strict recoveries | Unflagged unmodified-star fits |
| --- | ---: | ---: | ---: |
| production_harmonic | 6 / 27 | 6 / 27 | 0 |
| weak_harmonic | 7 / 27 | 7 / 27 | 0 |
| cycle_excluded | 6 / 27 | 6 / 27 | 0 |

The cycle-excluded variant recovered six strict cases, compared with seven for the stronger harmonic comparison. It lost one recovery made by that comparison and failed the development gate. It is not adopted.

The unmodified Wolf 1069 alias present after one pass was absent in all three methods after multiple passes. This does not uniquely support the cycle-excluded idea. The injected cases use a new seed, so recovery totals cannot be compared directly with the earlier one-pass experiment. Case labels recur between suites, but their periods and phases differ.

These are three inspected development stars, with box-shaped injections before binning and detrending. This is not a survey completeness estimate, calibrated false-alarm rate, invention-priority claim or new-planet discovery.

- [Frozen protocol](../../../docs/EXPERIMENT_MULTIMODE_CYCLES.md)
- [New paired cases and source hashes](plan.json)
- [Complete results and paired losses](results.json)
- [Driver](../../../scripts/multimode_cycle_experiment.py)

Reproduce with `python scripts/multimode_cycle_experiment.py --workers 3` after downloading the listed stars' light curves.
