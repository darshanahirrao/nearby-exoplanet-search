# Twenty-star expanded-coverage pilot

Select the first 20 rows of the published unused-coverage inventory, unchanged.
They contain 360 existing sectors and 390 unused 120-second SPOC sector products.
Selection uses only the existing catalogue metadata and previously examined
flux scatter; freeze and publish the selection, executable code, product URIs
and original input hashes before fetching additional flux.

Use the `coarse_only` revision selected by the completed 240-run confirmation
and retained by the real TOI-700 d control. Verify those exact prerequisites
through the original revised-pilot preparation code. No failed enlarged-shortlist
variant is adopted. This survey tests the opportunity provided by more archived
observations; it is not a new method comparison or a measured sensitivity gain.

Download the 390 products into `data/coverage_lightcurves/<TIC>/`, preserving
every original directory and result. Verify identifiers, sectors, file sets and
hashes, and freeze the complete download manifest before search. Reuse the exact
original loader with only that data-directory string changed; concatenate
original and added processed samples only after verifying sector separation and
unique timestamps. Retain unfiltered and filtered curves for every target.

Reuse the original revised-pilot worker and receipt checker, changing only the
loader binding and output-directory suffix. Apply the same sector-local
three-pass harmonic processing, physical-duration coarse seed selection,
original fine grid, two trial slots, whole-sector split and all screening
thresholds. Freeze the fitted training parameters before evaluating this run's
held sectors. Some old sectors have been examined previously; this is an
exploratory reanalysis, not fully untouched confirmation data or population-level
validation. Catalogue matching follows holdout evaluation.

Three numerical workers each use the existing two-thread BLS adapter. An
interrupted incomplete target is preserved for inspection; completed receipts
are reused only after hash and frozen-parameter checks. Preserve and export all
trial fits and flags, including negative results. Every unflagged trial requires
individual astrophysical vetting. The distinct-star count remains 1,031.

```sh
python scripts/coverage_pilot.py prepare
# Publish the frozen plan before downloading the added observations.
python scripts/coverage_pilot.py download
python scripts/coverage_pilot.py run --workers 3
```

Receipt `plan_sha256` values reference the post-download `execution_plan.json`,
which includes hashes of the preregistered selection and complete download
manifest. Neither a completed run nor an unflagged fit constitutes a discovery,
a validated planet, established habitability or a methodological breakthrough.
