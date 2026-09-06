# Nearby Exoplanet Search

An open, reproducible search of public TESS observations for overlooked transiting
planets around nearby cool stars, emphasizing small planets receiving temperate
irradiation. Numerical analysis runs locally; no paid model API is needed.

**Work in progress. No new or validated planet is claimed.** A habitable-zone orbit
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
python scripts/catalogs.py

# Known TOI-700 calibration; never a discovery.
python scripts/download.py --tics 150428135 --max-sectors 0 --workers 1
python scripts/search.py --tics 150428135 --max-signals 5 --tag _calibration

# Begin with a small discovery batch.
python scripts/download.py --count 10 --max-sectors 18 --workers 3
python scripts/batch.py --target-list target_batch_0_10.csv --workers 2
```

Outputs under `results/<TIC>/` include the processed light curve, frozen discovery
fit, held-back checks, catalogue matches and screening flags. Unflagged signals
still require detailed astrophysical vetting. Exact reruns require matching
catalogue snapshots and FITS hashes; upstream catalogues change over time.

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
