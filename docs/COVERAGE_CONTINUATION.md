# Remaining 45 stars: expanded-coverage continuation

After the completed first 20-star batch yielded no fit passing every screen,
select all remaining rows 21–65 of the unchanged published
`reports/unused_coverage/inventory.json`. These 45 previously searched stars
have 810 original and 887 unused sector products. Freeze the executable wrapper,
selection, exact product URIs, old input hashes and prior batch results, then
publish the plan before downloading the 887 additional products.

Use the existing [coverage protocol](COVERAGE_PILOT.md) and `coarse_only` method
unchanged. `coverage_continuation.py` derives preparation from the frozen pilot
with guarded substitutions limited to the target slice, expected counts, report
directory and provenance sources. It calls the original download and execution
functions with only their report-directory binding changed. The 45 target IDs
are disjoint from the first 20, so the existing per-target extra-data and result
directory conventions cannot overwrite that batch. Reverify the prior completed
pipeline comparison, known-planet controls and complete original input sets.

Retain the same preprocessing, sector split, two-fit cap, training freeze,
screening thresholds, two BLS threads per worker, three numerical workers,
download integrity checks and completed-output receipt checks. Publish every
retained fit, all flags and an input/frozen-parameter/arithmetic audit. Review
any unflagged fit individually before interpreting it as a possible planet.

This is exploratory continuation after seeing the earlier negative batch. It
does not establish method novelty, population completeness, an independent
method comparison, a discovery or habitability. Old observations were examined
previously; only the additional products are unexamined at selection time.
No failed method is adopted. The distinct-star count remains 1,031.

```sh
python scripts/coverage_continuation.py prepare
# Publish the frozen plan and code before downloading additional observations.
python scripts/coverage_continuation.py download
python scripts/coverage_continuation.py run --workers 3
```

The new report directory is `reports/coverage_continuation/`. As in the first
batch, each result receipt references the post-download execution-plan hash,
which links the pre-download selection plan and complete download manifest.
