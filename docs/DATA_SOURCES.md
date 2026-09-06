# Data sources and acknowledgements

The MIT license covers project code and original documentation. Third-party data,
publications and software retain their own terms and acknowledgement requirements.

| Source | Use |
| --- | --- |
| [Revised TESS HZ Catalogue](https://arxiv.org/abs/2101.07898), [CDS tables](https://cdsarc.cds.unistra.fr/ftp/J/AJ/161/233/) | Targets and stellar estimates |
| [MAST TESS archive](https://archive.stsci.edu/tess/) | SPOC light curves |
| [ExoFOP-TESS](https://exofop.ipac.caltech.edu/tess/) | TOI and community-TOI checks |
| [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/) | Confirmed-planet checks |
| [Astropy BLS](https://docs.astropy.org/en/stable/timeseries/bls.html) | Transit search |
| [Lightkurve](https://lightkurve.github.io/lightkurve/), [Astroquery](https://astroquery.readthedocs.io/) | Archive access |

This research uses public TESS observations obtained through MAST. TESS is a NASA
Explorer mission. Publications must include the current mission, archive,
catalogue, SPOC processing and software citations required by their providers.

`data/catalogs/manifest.json` records URLs and hashes. Observation provenance is in
`data/download_status/<TIC>.json`; curated exports go in `provenance/`. Hashes verify
byte identity but do not make evolving remote catalogues immutable. Exact reruns
require the same snapshots and products.

`provenance/catalogues/` preserves the original CDS and NASA Archive bytes in
deterministic gzip files. The ExoFOP snapshots contain only the numeric/identifier
columns used by the pipeline, preserving their original strings. The snapshot
manifest records original-download, derived-input, and compressed-file hashes
separately. `catalogue_snapshot.py restore` validates all files before restoring
them into an empty catalogue directory. These attributed third-party data are
not relicensed under the project's MIT code license.
