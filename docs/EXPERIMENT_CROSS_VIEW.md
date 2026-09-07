# Experimental method: prediction across observing geometries

Status: an original project hypothesis under test, not an established novel
algorithm, discovery, or replacement for the current search.

## Physical idea

A transit removes light from one fixed sky position. The mapping of that position
to detector pixels changes between observations. A detector artifact instead
follows detector coordinates; a blended eclipsing star follows a different sky
position. Collapsing the pixels into one light curve discards this distinction.

Fit the deficit's sky position using training sectors only. Freeze that position
and the temporal ephemeris. Predict the deficit's location in a reserved sector
through its independently supplied WCS. Compare that prediction with the intended
star and a detector-fixed alternative, while calibrating the comparison against
out-of-event images. This is a prospective prediction across views, rather than
allowing every sector to independently choose its best position.

The first prototype uses a simple Gaussian spatial template with width fixed in
advance. It profiles a single flux amplitude at each fixed location. It is not a
precision TESS PRF model, and an unresolved companion can remain indistinguishable.
Its first test is deliberately limited to difference images: synthetic signals
are added to real out-of-event difference maps with widths and offsets that differ
from the fitting template. Success there would justify a later raw-pixel test;
it would not demonstrate end-to-end planet sensitivity.

## Experiment fixed before evaluation

- Real fields: TIC 448416124 (sectors 9, 36, 63), TIC 408232559 (5, 32, 6), and
  TIC 282923395 (14, 48). The last listed sector in each field is reserved.
- Evaluate the already inspected contaminating/variable signals as case studies.
  These are not untouched discovery data or evidence of novelty.
- For simulations, derive noise maps from fixed off-event phase shifts of the
  existing trial ephemerides. Exclude overlap with the recorded event windows.
- Use training data to choose a position and held-view data only to evaluate
  the frozen prediction. No held-view localization is allowed in the new score.
- Compare with the current positive-core centroid and aperture-sum diagnostics
  on the same data. Report both missed target signals and falsely accepted
  displaced signals, including ambiguous cases.
- Use distinct deterministic development and evaluation seeds. Preserve all
  trial labels and scores; do not report the best-performing subset.
- Adoption requires an advantage on fresh cases without a material loss of
  target-signal recovery. A failed experiment is retained and the baseline stays.

## Relationship to prior work

Difference-image localization and pixel-level source probabilities already
exist. Transit-APP (2025) is relevant prior art; its title is *Transit-APP: A
Centroid-free Method of Identifying Background Transit False Positives*
([NASA record](https://ntrs.nasa.gov/citations/20250003461)). The proposed point
to investigate is frozen cross-view prediction with empirical counterfactual
images, rather than a claim to have invented difference imaging. A deeper prior
art check is required before claiming methodological novelty.

This experiment addresses false-positive discrimination and source attribution.
It does not by itself make invisible transits detectable, identify habitability,
or guarantee a new planet. It complements the continuing full-coverage search.
