# Minimize noise on transit timescales with baseline-feasible constraints

The preceding relative-response experiment improved rapid scatter but missed its
two-hour noise gate. This revision changes the objective to the worst normalized
training variance of compensated windows lasting 1, 2 and 4 hours. Each window
subtracts the mean of its two neighboring windows, rejecting a local constant
and linear trend. Four bin origins per duration reduce dependence on grid phase;
windows with inadequate coverage are excluded. All covariances use training
data only, robust clipping and fixed diagonal shrinkage.

Retain the preceding target-response bounds and nominal and empirical rapid-noise
caps. Also cap broad training variance at the baseline value. The original
aperture is feasible for all constraints. Minimize the maximum of the three
transit-timescale variance ratios. Fall back to the original aperture for any
optimization failure or constraint violation. The objective and constraints do
not guarantee performance on actual reserved observations or unmodeled source
footprints.

Use the same eight already-inspected sectors as development data. Keep the
preceding gate unchanged: median reserved two-hour scatter ratio at most 0.900;
every reserved adjacent-difference and two-hour ratio at most 1.050; and at least
0.990 relative target response for every in-range random footprint draw.
Report the same wider footprint stress draws and fallback frequency. Passing
warrants a separately frozen fresh-data experiment, not production adoption.

Record code and protocol hashes and seed before running this revision. This is
a project-specific optimization experiment using established constrained
estimation and temporal filtering; originality and discovery are unestablished.
