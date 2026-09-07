# Apply the transit-duration prior before seed selection

The search-bottleneck diagnostic found that broad seed fits can crowd out a
measurable injected transit before later physical vetting rejects those fits.
Test an early duration prior against the original search and an equal-cleaning
comparison. BLS, physical duration priors and harmonic correction are established
ideas; this integration is a project hypothesis, not an invention-priority claim.

Use the original combined-season period grid, thirty-minute coarse samples,
ten-minute refinement, two retained fits, whole-sector holdout, and all original
checks. Partition each sorted period grid into bands of width at most 1.25 in
period ratio. In each band use duration factors 0.35/0.5/0.7/1/1.25/1.5 times
the central circular duration at its shortest period, assuming the catalogue star
and a two-Earth-radius planet. Clip durations to the existing refinement bounds
of 0.015–0.3 days. Apply this family in both coarse and fine scans. The original
grid density remains fixed; this is not a claim of complete coverage of all
possible short transits, eccentric orbits or uncertain stellar parameters.

Compare three methods:

1. Original single-pass harmonic correction and unrestricted duration search.
2. Up to three lower-threshold harmonic corrections and unrestricted durations.
3. Exactly the same cleaning as method 2, with the physical duration family.

All modes are fit separately within sectors. Holdout flux cannot change the
training ephemeris. Radius and period truths are hidden from the search; only
the shared target-star catalogue row supplies the duration prior. The two-planet-
radius assumption is fixed across all cases, not fitted to the injected radius.

Freeze 45 fresh raw-light-curve box injections with seed 202609083 on five
development stars: TIC 232970271, 352617553, 378527773, 219223742 and 397098265.
Each has three fresh periods/phases crossed with radii 0.6/0.8/1 Earth radii.
Also run the five unmodified stars, yielding 150 paired method runs. These stars
were studied before; this is a new case set, not independent new-star validation.

The development gate requires at least two additional strict recoveries over
the stronger comparison, no lost strict recoveries from either comparison, no
increase in unflagged unmodified-star fits over the equal-cleaning comparison,
and no execution errors. Retain the benchmark's original definition of strict
recovery: period and endpoint timing agreement, nominal training SNR at least 7,
three training events, two held-sector events and held-sector SNR at least 5.
Also report recovery passing every astrophysical screening flag separately.

Only a pass warrants an unchanged new-star experiment with realistic transit
shapes and a fresh unmodified-star search. Box injections favor BLS. The null
diagnostics are not simulated planet-free stars and do not calibrate false-alarm
probabilities. No discovery, population completeness or novelty is established.
