# New-star confirmation of the early duration prior

This protocol and its cases are frozen before viewing these stars with the new
method. Execute only if the physical-duration development gate passes. Retain
that method unchanged; passing this follow-up only supports a broader exploratory
search, not a discovery, completeness measurement or methodological novelty.

Select two stars from each TESS magnitude interval [8,11), [11,12.5), and
[12.5,14.01). Eligible stars are already downloaded, have at least six sectors,
catalogue radii 0.1–0.4 solar radii and Earth-irradiation periods at most 20 days,
and are not known TOI/CTOI hosts. Exclude the five development stars and earlier
pixel/known-planet/performance controls listed in the executable selection rule.
Sort each magnitude group by TIC, then sample without replacement with seed
202609084. These stars have already undergone the original survey but were not
used for development of this duration method. No new-method score selects them.

Freeze three fresh periods/phases per star, crossed with radii 0.6/0.8/1 Earth
radii. Give the three orbits impact parameters 0.2/0.55/0.85 and quadratic
limb-darkening coefficients (0.2,0.2)/(0.4,0.2)/(0.6,0.1), respectively. These are
representative fixed models, not measured limb-darkening coefficients of the
actual stars. Use circular orbits, batman 2.5.3, and seven samples per 120-second
exposure. Inject multiplicatively into PDCSAP before our binning, normalization,
detrending and variability fits. This omits upstream SPOC processing losses.

The 54 physical transit models and six unmodified stars are run with all three
unchanged comparisons, totaling 180 method runs. Neither the search nor the
duration prior receives the injected period, phase, impact parameter, radius or
limb-darkening values. The prior uses only the shared catalogue star and its
fixed two-Earth-radius assumption. Preserve the whole-sector holdout and
original strict recovery definition; separately report all-screening-check
recoveries. No held-sector flux may adjust the training ephemeris.

Keep the development gate: at least two more strict recoveries than the stronger
comparison, no lost strict recovery from either comparison, no additional
unflagged fits on the unmodified stars relative to equal-budget harmonic cleaning,
and no execution errors. Unmodified stars are not proven planet-free; their
scores do not calibrate a false-alarm probability. Retain every failure and
source hash. Do not tune after opening the results.

Model reference: [Kreidberg (2015)](https://arxiv.org/abs/1507.08285);
[exposure integration](https://lkreidberg.github.io/batman/docs/html/tutorial.html).
Physical duration priors are established, including in
[Hippke and Heller (2019)](https://arxiv.org/abs/1901.02015).
