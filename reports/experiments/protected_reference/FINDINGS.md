# Protected periodic-reference result

The development gate failed. The four additional pixel views were not evaluated.
This experiment is not adopted by the production search.

The fixed spatial reference removes the nominal target footprint before averaging
three harmonics of the neighbor's 0.377694-day signal. A finite family of modeled
transits limits subtraction strength; explicit injected-pixel calculations check
the analytic depth-response formula. This is a finite-model signal-transfer test,
not blind planet recovery or a claim of methodological novelty.

| Development measure | Result | Required |
| --- | ---: | ---: |
| Median two-hour scatter / aperture | 0.9625 | ≤ 0.90 |
| Worst rapid or two-hour scatter / aperture | 0.9991 | ≤ 1.05 |
| Median periodic RMS / aperture | 0.6453 | ≤ 0.50 |
| Median two-hour scatter / direct harmonic subtraction | 1.1895 | ≤ 1.05 |
| Minimum fresh modeled depth response | 0.9971 | ≥ 0.99 |

Subtraction strength was limited to 0.438 and 0.382 in sectors 17 and 58.
The model preserved transit depth well, but gained too little noise reduction and
underperformed direct harmonic subtraction. The latter removes the fitted modes
exactly by construction, which is not itself evidence of good transit recovery.

The exact diagonal photon-noise calculation includes shared-pixel covariance;
correlated noise across times remains. Spatial footprints are approximate Gaussians.
TIC 608579111 is a positional association with the variable difference-image source,
not a uniquely confirmed identification or a newly established variable star.

Related established work includes [PLD and injection tests in EVEREST](https://arxiv.org/abs/1607.00524)
and [STScI's PLD workflow and transit masking](https://spacetelescope.github.io/mast_notebooks/notebooks/K2/removing_instrumental_noise_using_pld/removing_instrumental_noise_using_pld.html).
These provide context; this experiment has not established priority over existing
linear detrending or source-separation methods.

See [frozen plan](plan.json), [full development results](development.json), and
[protocol](../../../docs/EXPERIMENT_PROTECTED_REFERENCE.md).
