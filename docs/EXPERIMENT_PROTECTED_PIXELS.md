# Experimental extraction with a protected target response

Status: next method-development experiment, not a discovery or a novelty claim.
The two cross-view prediction variants did not establish a useful advantage over
ordinary spatial filtering. This experiment addresses extraction of the light
curve itself, where information from separate pixels can still be retained.

For a vector of pixel fluxes, form a weighted sum. Choose weights that suppress
correlated variations while constraining the response to a family of possible
target-star footprints to stay between 0.97 and 1.03. If the actual target
footprint belongs to that tested family, a dimming on the target cannot be
attenuated by more than 3% by this linear extraction. This statement is about
the extraction operator, not the full transit-search pipeline or unknown real
point-spread functions.

The family spans subpixel position and Gaussian width uncertainty. A separate
stress set will use unseen footprints. This is related to constrained minimum
variance estimation and optimal photometry; invention priority is unestablished.
The project hypothesis is whether explicit preservation constraints improve
practical contamination suppression without sacrificing target-transit response
in these public TESS images.

Use the eight available target-pixel sectors in TIC 448416124, TIC 408232559 and
TIC 282923395. Fit the pixel covariance and weights on the first half of each
sector; evaluate noise and injected target response on the second half. Preserve
the fixed SPOC aperture extraction as a comparison. Do not use the held-half
flux to choose weights. No change to the production search is allowed based on
this small extraction test alone.

Freeze all numerical settings and a random seed in a machine-readable plan before
evaluation. Record constraints, failures, training and held-half scatter, target
response across unseen footprints, and any noise amplification. A mathematical
constraint passing on the modeled family does not prove preservation of all
real stars; a worse recovery tradeoff prevents adoption.
