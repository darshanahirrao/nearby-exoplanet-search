# Nearby Exoplanet Search

An open, reproducible search of public TESS observations for overlooked transiting
planets around nearby cool stars, emphasizing small planets receiving temperate
irradiation. Numerical analysis runs locally; no paid model API is needed.

**Initial campaign complete: 1,031 distinct stars searched; no surviving planet
candidate or new discovery.** A habitable-zone orbit
does not establish habitability. See [research status](reports/STATUS.md),
[methods and limitations](docs/METHODS.md), and [data sources](docs/DATA_SOURCES.md).

## Reproduce the analysis

Use Python 3.12. `requirements.lock.txt` records the full environment;
`requirements.txt` lists direct dependencies. Archive retrieval requires internet
access and can download gigabytes depending on batch size.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m unittest discover -s tests -v
# Optional: use the inputs from the published run in a clean checkout.
python scripts/catalogue_snapshot.py restore
python scripts/catalogs.py

# Known TOI-700 calibration; never a discovery.
python scripts/download.py --tics 150428135 --max-sectors 0 --workers 1
python scripts/search.py --tics 150428135 --max-signals 5 --tag _calibration_v2
python scripts/refine.py --folders results/150428135_calibration_v2 --workers 1

# Begin with a small discovery batch.
python scripts/download.py --count 10 --max-sectors 18 --workers 3
python scripts/batch.py --target-list target_batch_0_10.csv --workers 2

# Freeze timing refinement before checking the remaining observations.
python scripts/refine.py --all-screened --workers 2
python scripts/variability.py --all-screened --workers 2
python scripts/longbaseline.py --all-screened --workers 2
python scripts/audit_inputs.py
python scripts/audit_results.py
python scripts/summarize.py
```

Outputs under `results/<TIC>/` include the processed light curve, frozen discovery
fit, held-back checks, catalogue matches and screening flags. Unflagged signals
still require detailed astrophysical vetting. Exact reruns require matching
catalogue snapshots and FITS hashes; upstream catalogues change over time.
The checked catalogue restore includes every field used by the pipeline, with
ExoFOP free-text columns omitted. It refuses to replace differing local inputs.
Raw FITS files are retrieved from MAST, with exact product identifiers and hashes
listed in the observation manifest.

The initial pilot and the fresh refinement tests can be reproduced with:

```sh
python scripts/download.py --tics 219223742 397098265 232970271 --max-sectors 18
python scripts/injections.py --tics 219223742 397098265 232970271 --seed 20260907
python scripts/injections.py --tics 219223742 397098265 232970271 --seed 20260908 --refine --suite injections_refined_fresh
python scripts/injections.py --tics 219223742 397098265 232970271 --seed 20260908 --refine --clean --suite injections_clean_paired
python scripts/injections.py --tics 219223742 397098265 232970271 --seed 20260909 --refine --clean --suite injections_clean_fresh
python scripts/injections.py --tics 219223742 397098265 232970271 --seed 20260910 --clean --longbaseline --suite injections_longbaseline_fresh
```

To overlap downloads and screening for a bounded tranche, use
`python scripts/run_campaign.py --offset 0 --count 10`. It then runs timing
refinement, preliminary variability diagnostics, and local evidence exports.
It does not assign planet validation or publish results automatically.

The separate search for additional planets in confirmed-planet systems uses a
fixed host list. Its transit masks and results are recorded separately:

```sh
python scripts/known_residual.py --prepare
python - <<'PY'
import json, subprocess, sys
ids = json.load(open("provenance/known_host_search_plan.json"))["targets"]
subprocess.run([sys.executable, "scripts/download.py", "--tics",
                *map(str, ids), "--max-sectors", "18"], check=True)
PY
python scripts/known_residual.py --workers 2
```

`audit_inputs.py` checks FITS target identities and time references and exports
byte hashes for every local telescope input. `audit_results.py` compares saved
ephemerides with the records frozen before holdout evaluation, checks available
source hashes, and reports execution coverage. Use its `--require-complete` flag
only after reproducing all [1,000 selected targets](provenance/main_target_selection.csv)
and the separate known-host list; a small quickstart batch is intentionally incomplete.
The [pixel-vetting example](reports/vetting/448416124/disposition.json)
shows why a repeatable dip can still come from a different star.

An optional [accelerated runner](docs/PERFORMANCE.md) preserves the original
period grid and scientific checks. Three real-input comparisons, including the
TOI-700 control, produced identical scientific outputs and a measured aggregate
speed ratio of 1.79. Use `python scripts/progress.py` for a compact live status.

We also test original project hypotheses against existing methods. The first
[cross-view experiment and ablation](reports/experiments/cross_view/FINDINGS.md)
did not establish a sufficient advantage over ordinary spatial template fitting.
The [uncertainty variant](reports/experiments/cross_view_uncertainty/FINDINGS.md)
accepted more displaced-source signals, and
[response-constrained pixel extraction](reports/experiments/protected_pixels/FINDINGS.md)
increased short-timescale noise in all eight tested sectors. These negative
results are preserved. None of these prototypes replaced the search, and no
methodological novelty or breakthrough is established.

Two subsequent [noise-capped](reports/experiments/relative_pixels/FINDINGS.md) and
[transit-timescale](reports/experiments/multiscale_pixels/FINDINGS.md) extraction
revisions reduced rapid scatter in all eight development sectors, but missed
their predeclared transit-timescale improvement gate. They remain experimental.

The [cycle-excluded variability trial](reports/experiments/cycle_excluded/FINDINGS.md)
then gained one strict recovery in 27 paired faint-signal injections, with no lost
comparison recoveries. That also missed its predeclared gain threshold and has
not replaced the production method.

Two [source-specific](reports/experiments/periodic_source/FINDINGS.md)
[pixel-filter tests](reports/experiments/protected_reference/FINDINGS.md) also
missed their improvement gates. Current work follows a measured
[search bottleneck](reports/experiments/search_bottleneck/FINDINGS.md): broad,
implausible seed fits can displace detectable injected transits before vetting.

## Repository map

| Path | Purpose |
| --- | --- |
| `scripts/` | Retrieval, physical estimates, search and batch orchestration |
| `tests/` | Offline scientific consistency checks |
| `docs/` | Methods, assumptions, limitations and data acknowledgements |
| `reports/` | Curated calibration, search and vetting results |
| `provenance/` | Source hashes and exact target identifiers |
| `data/`, `results/`, `logs/` | Local generated files, excluded from Git |

## Evidence standard

Recover known transits. Inject synthetic transits into real data and measure
recovery. Retain non-detections and rejected signals. Freeze hypotheses before
checking separate observations. Inspect individual events, alternate flux
extractions, pixel centroids, nearby sources and current catalogues. Quantify
noise and stellar-parameter uncertainty. New observations may still be necessary.

This project is developed with AI assistance. Scientific claims depend on
reproducible measurements and independent checks; generated explanations are not
evidence. Corrections are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

The [MIT license](LICENSE) covers project code and original documentation.
Third-party data and software retain their own terms and citation requirements.
