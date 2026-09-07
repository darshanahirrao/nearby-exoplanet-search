# Fixed-ephemeris follow-up of TIC 233738219

The primary question is whether the unexplained 26.316459-day fit repeats in
archived observations not previously downloaded or used by this project. The
35.394150-day fit is included as a disclosed comparison. This is follow-up of
one existing target; the distinct-star count does not increase. Neither fit is
a validated planet or an established new discovery.

Preparation selects every unused sector in the existing 120-second SPOC product
table, excluding the 18 previously downloaded sectors. Selection uses only
metadata. The code, exact ephemerides, original-input hashes, requested archive
identifiers and checks are frozen in `reports/vetting/fresh_sector_followup/plan.json`
and published before the new flux is downloaded. New files use a separate
directory so every prior search and experiment continues to see its original
inputs.

The original loader is reused with only its data-directory string replaced.
Use the original quality mask, ten-minute binning, median trend and error floor,
followed by the frozen three-pass harmonic filter. Analyze all selected sectors
together, at exactly the existing periods, epochs and durations. There is no
period, phase or duration optimization. Verify sector and processed-timestamp
separation from the original data. Incomplete downloads prevent analysis.

For both PDC and SAP, report the original event-depth statistic and the quadratic
continuum diagnostic with two-sided coverage and the original outer radius,
before and after harmonic filtering. The nominal recurrence screen requires at
least three measurable events, at least 60% positive depths, and nominal SNR of
at least 5 in both of the PDC statistics after filtering. Display every planned
result whether it passes or fails. Also report all intervening rotation phase
classes, using the nearest integer ratio to the published 1.316-day rotation
period, with no extra phase search.

The screen is not a false-alarm calibration. Harmonic models are fitted within
each new sector; this is unsupervised preprocessing, not access to new data for
timing optimization. A recurrence result still needs shape, stellar-variability,
source and false-positive assessment. A failure does not show the star has no
planets. This protocol neither alters an earlier experiment nor authorizes
adoption of either failed shortlist method for a survey.

```sh
python scripts/followup_portfolio_trials.py prepare
# Publish the frozen plan before the following operations.
python scripts/followup_portfolio_trials.py download
python scripts/followup_portfolio_trials.py analyze
```
