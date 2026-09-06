# Contributing

Contributions improving reproducibility, sensitivity and false-positive rejection
are welcome. Describe the scientific question, data product and proposed check.
Include a meaningful test or explicitly labelled calibration experiment.

Preserve previous outputs when changing methods. Use a new output tag and record
the code revision. Once used for tuning, data are no longer untouched validation.

For a signal, supply the TIC identifier, sectors, product identifiers, period,
epoch with time convention, duration, individual event depths, unsuccessful checks,
and exact reproduction steps. Do not upload credentials or large raw FITS files.

A threshold crossing is not a validated planet. Novelty requires current catalogue
and literature checks. Planet validation requires astrophysical false-positive
analysis and may require new observations.

Run offline checks with `python -m unittest discover -s tests -v`.
