# Exclude an observing cycle from its own variability template

The search's dominant false signals are integer multiples of faster variability.
This experiment tests a robust phase template that can represent sharper shapes
than the current three-harmonic model. For a fixed fitted variability period,
assign complete cycles to three groups. Predict each group using phase-bin
medians from the other groups. A dip cannot directly enter its own group's
template. Interpolate only when at least 75% of bins have adequate training data.
Apply the correction only when the sector's robust scatter falls by at least
0.5%; retain the original error floor. This selection is part of the algorithm
and is rerun after each injection.

The variability period is estimated from the whole sector, so the group exclusion
does not guarantee that a transit cannot influence that estimate. Repeated
transits at commensurate phases can also contaminate other groups. These are
testable limitations, not a universal transit-preservation proof. Preprocessing
is sector-local, including reserved sectors, and never uses a proposed planet's
ephemeris. Search ephemerides are frozen before reserved-sector scoring.

Compare three methods on identical raw-light-curve injections: the production
harmonic filter (power threshold 0.10), the same harmonic filter at threshold 0.02,
and the cycle-excluded median filter at threshold 0.02. The lower-threshold
harmonic comparison prevents crediting a threshold change to the template idea.
Reuse the unchanged combined-season search, two retained peaks and strict
training/held-sector recovery checks. Parallel BLS preserves the existing grid.

Freeze 27 injected cases on TIC 232970271, Wolf 1069 / TIC 352617553, and
TIC 378527773, using three periods/phases crossed with radii 0.6, 0.8 and 1.0 Earth
radii. Also search each unmodified star as a negative diagnostic. These are
inspected development stars, not independent survey validation. Raw injections
precede binning, detrending, variability fitting and the search.

The development gate requires at least two more strict injected recoveries than
the stronger harmonic comparison, no loss of any strict recovery from either
harmonic comparison, and no increase in unflagged fits on the three unmodified
stars relative to the lower-threshold harmonic comparison. Negative-diagnostic
counts are not a calibrated false-alarm rate. Passing would justify a fresh,
realistic-transit experiment on new stars; it would not establish a planet or
production readiness.

Modeling rotations with other rotations is prior art, including
[Rizzuto's LOCoR](https://acrizzuto.wixsite.com/astro/research). The project-specific
variant here uses disjoint cycle groups, median templates and the explicit paired
comparison above. Its novelty relative to the full literature is unestablished.
