# Real-signal control for the frozen pipeline revisions

Run all four complete pipelines on the same 37-sector TOI-700 calibration light
curve used by the previous corrected control. Use its recorded catalogue star,
original period range, sector split, two retained fits and holdout checks. This
star and its known signals were inspected previously; this is a real-signal
regression control, not independent target selection or a discovery search.

Recompute the original single-pass harmonic pipeline, the three-pass lower-
threshold harmonic comparison, and both frozen seed-search revisions. Hash the
input, prior star record, catalogue truth and all source files before evaluation.
The known periods and epochs are used only to score the resulting frozen fits;
they do not enter period selection, detrending or fitting. Use one BLS numerical
thread per call to limit competition with the concurrent six-star experiment.

For each returned signal, match the same catalogue period within 0.1% and require
catalogue-prediction timing agreement at both ends of training within 0.75 of the
catalogued transit duration. Report matches, strict recovery using the same
training SNR/event and held-sector SNR/event cuts, and every screening flag.
The comparison only tests known signals within the configured search range.

The prior pipeline recovered the known roughly 37.424-day planet but did not
retain the roughly 27.810-day signal among its two fits. Retain every outcome,
including regressions. This does not replace the independently frozen physical-
injection comparison or establish completeness, new planets or methodological
priority.
