# Faster execution with unchanged scientific calculations

The optional accelerated runner splits the original period array into disjoint
chunks, evaluates them using Astropy's unchanged fast BLS implementation, and
restores their original order. Astropy releases the Python GIL during that C
calculation. Every input sample, trial period, duration, oversampling setting,
retained peak, physical gate and held-back observation remains the same.
Fine grids use the original serial call. BLAS and OpenMP are limited to one
thread each to avoid nested oversubscription and changes in reduction order.

Three complete serial-versus-parallel searches used saved real observations:

| Target | Serial seconds | Parallel seconds | Speed ratio |
| --- | ---: | ---: | ---: |
| TIC 22535327 | 20.35 | 11.04 | 1.84 |
| TIC 232970271 | 18.54 | 10.00 | 1.85 |
| TOI-700 / TIC 150428135 | 153.51 | 86.38 | 1.78 |

All scientific output fields, including both fitted periods, depths, durations,
epochs, event measurements, held-back statistics and screening decisions, were
identical. Only wall times and freeze timestamps were excluded from comparison.
TOI-700 d was recovered at the same period. The aggregate speed ratio was 1.79,
equivalent to about 44% less wall time in these benchmarks. This is a small
comparison under concurrent machine load, not a guaranteed survey speedup.
[Machine-readable evidence](../reports/performance/parallel_bls.json) records
input hashes, environment and individual timings.

The live run switched after 685 completed combined-season results. Those files
were retained byte-for-byte; three unfinished target calculations were restarted.
The [transition checkpoint](../provenance/acceleration_checkpoint.json) records
the preserved hashes. Remaining work uses three target workers with two BLS
threads each. Larger input frames start first to reduce a slow final worker.

```sh
python scripts/benchmark_acceleration.py --tics 22535327 232970271 150428135 --threads 2
python scripts/accelerated_longbaseline.py --all-screened --workers 3 --threads 2
python scripts/progress.py
```

Run the accelerated and original combined-season runners separately. Their
outputs share a destination. The new runner checks data hashes and frozen fit
consistency before accepting a cache, writes execution metadata atomically, and
returns failure if any worker fails. Its lock prevents two accelerated runners
from overlapping; the historical original runner does not take this lock.
Do not edit numerical modules during a running search because their hashes are
recorded with the results.

Twelve offline tests cover the original scientific checks, exact comparison
against Astropy on a gapped heteroskedastic data set with an unsorted grid, and
rejection of corrupted restart inputs or inconsistent frozen fits. These checks
also include training-only localization in the separate experimental prototype.
They protect computational consistency, but do not establish sensitivity on
every star or validate a planet.

`progress.py` returns compact live counts and an explicit queue of unreviewed
unflagged fits. This avoids repeatedly sending thousands of per-event records
to a language model. Its snapshot can change during writes; the full input and
result audits remain necessary before publishing a final research result.
