# Cancel a measured periodic spatial nuisance while protecting the target

TIC 378527773's approximately nine-hour variation is displaced from its target
position in sectors 17 and 58. This experiment tests whether specifically
suppressing that spatial variability improves the target extraction. This is a
conditional development hypothesis, not a revival or validation of the earlier
failed general pixel-extraction trials.

Keep the variability period fixed at 0.37769418149605544 days, as recorded by the
previous pixel-origin diagnostic. On the first half of a sector, fit three sine
and cosine harmonics plus a constant and linear time term to the pixels. Use the
covariance of the fitted harmonic component as the extraction objective. Choose
pixel weights that minimize this periodic component, subject to:

- response to each of 81 modeled target footprints between 1.00 and 1.03 times
  the fixed SPOC aperture's response;
- nominal photon-noise variance, empirical rapid-noise variance, and broad
  training variance no greater than their fixed-aperture values;
- bounded weights that include the original aperture as a feasible solution.

The modeled preservation property extends by linearity to convex mixtures of
the constrained footprints. It does not cover all actual point-spread functions.
The original aperture is a feasible fallback for numerical failures. No source
can be separated from a target with an identical spatial footprint on this basis.

Compare the new weights against the original aperture, the earlier constrained
broad-variance extractor, and the earlier multiscale extractor, using the same
inputs and footprint family. Freeze weights before evaluating the second half.
Measure rapid scatter, a compensated two-hour scatter statistic, the amplitude
of the periodic nuisance, and response to random target footprints. The two-hour
metric uses effective observing times to interpolate neighboring bin means;
this corrects the partial-bin timing asymmetry in the earlier metric.

Development uses sectors 17 and 58, whose pixel images were inspected already.
The development gate requires all of the following:

- median two-hour scatter at most 0.90 times the original aperture's;
- median paired two-hour scatter at most 0.95 times each earlier extractor's;
- neither development sector more than 5% worse than the aperture in rapid or
  two-hour scatter;
- median periodic-component RMS at most 0.70 times the aperture's;
- every in-range random target-footprint response at least 0.99 of the aperture's.

Only if this gate passes, use the unchanged method on sectors 18, 24, 25 and 52,
with the same gate applied across those four views. Their pixel-extraction outputs
were not previously inspected, but their scalar light curves were already part
of the main campaign; this is not an entirely untouched astronomical dataset.
No settings may be changed after reading development results under this plan.

Passing both stages would justify a separately frozen, full injection/recovery
test. A frozen-operator response check alone does not establish transit recovery.
These metrics are not false-alarm probabilities or evidence for a new planet.
Constrained spatial estimation and periodic nuisance modeling have prior art;
methodological novelty is unestablished.
