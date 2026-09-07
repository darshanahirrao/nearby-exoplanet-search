# Periodic-source spatial weights failed their development gate

The new objective reduced the median reserved two-hour scatter by 3.7% and the median periodic-component RMS by 13.6%. Neither met the preregistered thresholds of 10% and 30%, respectively. Its paired two-hour ratios were 0.957 versus broad-variance extraction and 0.990 versus multiscale extraction; both also missed the 0.950 requirement.

No development sector worsened in the checked noise statistics relative to the aperture, and the smallest in-range relative target response exceeded 1.0007. Those safeguards passing does not establish a useful improvement. The overall gate failed, so the four additional pixel views are not evaluated by this method under this protocol. It is not adopted.

| Sector | Method | Rapid / aperture | Two-hour / aperture | Periodic RMS / aperture |
| --- | --- | ---: | ---: | ---: |
| 17 | aperture | 1.000 | 1.000 | 1.000 |
| 17 | broad | 0.876 | 0.922 | 0.898 |
| 17 | multiscale | 0.938 | 0.917 | 0.843 |
| 17 | periodic_source | 0.995 | 0.932 | 0.892 |
| 58 | aperture | 1.000 | 1.000 | 1.000 |
| 58 | broad | 0.918 | 1.100 | 0.922 |
| 58 | multiscale | 0.917 | 1.031 | 0.936 |
| 58 | periodic_source | 0.978 | 0.993 | 0.836 |

These are extraction/noise measurements, not blind planet recovery rates. Modeled footprint protection is not a guarantee for every actual point-spread function. The experiment is conditional development on an inspected star; source identity and method novelty remain unestablished.

- [Frozen protocol](../../../docs/EXPERIMENT_PERIODIC_SOURCE.md)
- [Frozen inputs and code hashes](plan.json)
- [Complete development measurements and gate](development.json)
- [Code](../../../scripts/periodic_source_experiment.py)

Reproduce with `python scripts/periodic_source_experiment.py --stage development`. The assessment stage deliberately refuses to proceed after this failed gate.
