# Methods and verification boundaries

This exploratory, computer-assisted search is under active validation. Nominal
signal-to-noise statistics are not discovery probabilities.

## Targets

Tables 3 and 5 of [Kaltenegger et al. (2021)](https://arxiv.org/abs/2101.07898)
provide 6,492 distinct stars. Initial cuts: radius 0.10–0.65 solar radii;
temperature 2,600–4,500 K; distance at most 100 pc; TESS magnitude at most 14;
positive mass; recomputed Earth-irradiation period 3–90 days. A heuristic ranking
favors bright, small, nearby stars and deeper Earth-sized transits. Initial batches
exclude hosts listed in downloaded TOI and community-TOI snapshots; this does not
establish that the remaining hosts or signals are unknown.

## Data and preprocessing

Public SPOC 120-second TESS light curves come from MAST. An initial cap of 18
sectors retains early and late observations. TOI-700 (TIC 150428135), the known
calibration system, uses all available products. FITS originals remain unchanged;
download manifests preserve product identifiers and SHA-256 hashes.

Keep finite positive flux/error and quality flag zero. Normalize each sector,
split gaps over 0.3 days, bin to 10 minutes, and divide by a 1.5-day running median.
Remove 0.1 days at segment edges and upward excursions exceeding six estimated
white-noise standard deviations. Downward excursions remain for vetting. Errors
have a floor estimated from adjacent differences. This can suppress short transits
and retain correlated noise; injection/recovery and alternate extraction are needed.

## Discovery and holdout

Gaps over 100 days separate campaigns. The largest campaign is searched; the rest
are held back. With one campaign and at least four sectors, alternate sectors form
the holdout; otherwise there is no independent holdout. Detrending is segment-local.

Astropy box least squares searches a logarithmic period grid limiting approximate
phase drift to one quarter of the shortest trial duration. The range is 0.85 times
the inner empirical HZ period to 1.15 times the outer period, bounded by 1–100 days
and 0.48 times the discovery baseline. Durations span 0.025–0.25 days. Peaks are
refined on discovery data, then masked for up to four iterative searches. Known
short-period TOI transits are explicitly masked and documented when present.

`frozen_discovery.json` is written before evaluating holdout transits at the fitted
period and epoch. Period uncertainties are not yet propagated: long extrapolations
can miss real planets, so failure of this strict test does not disprove a planet.

## Preliminary gates

Flags cover known periods/harmonics; fewer than three discovery events; one event
dominating; odd/even depth differences; approximate radius outside 0.5–2 Earth
radii; period outside the empirical HZ; duration exceeding 1.6 times a central
circular transit; absent/insufficient holdout; holdout nominal S/N below 5; and BLS
nominal S/N below 7. Duration is a diagnostic; eccentric transits can be longer.

Passing means **requires detailed vetting**, not a validated planet candidate.
Required follow-up includes individual events, correlated-noise/false-alarm controls,
alternate detrending and SAP flux, secondary eclipses, pixel differences/centroids,
nearby sources, known variables, planets, TOIs, CTOIs and literature. Update stellar
parameters and propagate uncertainties. Independent observations may still be needed.

## Physical HZ estimates and catalogue consistency

`physics.py` implements Table 1 and equations 1–3 of the 2021 paper. Luminosity is
recomputed from stellar radius and temperature. Solar temperature is 5,772 K for
luminosity; the polynomial uses the paper's 5,780 K reference.

The CDS snapshot labels TOI-700 `PerEA=24.91`, `PerRV=33.99` days. Its radius and
temperature imply an Earth-equivalent period about 33.22 days; the separation
labels show the same apparent reversal. Original columns are preserved, while
search boundaries are calculated independently. This is a metadata consistency
observation, not a claimed scientific discovery.

HZ membership describes irradiation under stated atmospheric assumptions. It does
not establish rocky composition, water, habitability or life.
