# Confirm the complete pipeline revisions on other stars

The earlier training-qualification experiment failed its incremental-component
gate: it gained one strict recovery over the simpler revision, where two were
required. Its complete pipeline nevertheless gained three over the original
search and two over the stronger legacy harmonic comparison, with no lost strict
recovery. This new protocol investigates that combined observation independently.
It does not change the failed gate or activate the earlier unused assessment.

Keep both revisions frozen. Compare the original single-pass search, three-pass
lower-threshold harmonic cleaning with the original search, physical coarse seeds
with original fine fitting, and the same with early training qualification.
Use all four on exactly the six stars and 54 physical transit models already
frozen in `reports/experiments/realistic_duration/plan.json`, plus the six unmodified
stars. No method was previously run on those prepared cases. This yields 240 new
runs; none is a reuse of an executed physical-transit assessment.

Preserve the selected target identities, periods, phases, 0.6/0.8/1-Earth radii,
impact parameters, limb darkening, circular orbits and seven-point 120-second
exposure integration. Use the same raw PDCSAP injection adapter and all original
sector splits, error floors and holdout criteria. Hash and verify the original
template plan, catalogue, 70 FITS inputs and all implementation files. The six
stars were searched by the original campaign, but their outcomes with the new
methods and these physical injections are unseen at protocol freeze.

Evaluate each complete revision against both legacy pipelines. It qualifies for
a broader exploratory pilot only if it gains at least two strict recoveries over
the stronger legacy comparison, loses none of either legacy comparison's strict
recoveries, has at least as many recoveries passing every screening check as
either legacy comparison, and produces no more unflagged unmodified-star fits
than the three-pass harmonic comparison. Require strict gains over the stronger
legacy comparison on at least two distinct stars, and no execution errors.

If both revisions pass, prefer more all-screening recoveries, then more strict
recoveries, then less median run time. Report both results and every lost case.
Their component comparison remains descriptive; this protocol does not replace
the failed prior incremental-gain criterion. Choosing between two fixed revisions
on a small assessment sample is not proof of general population performance.
No tuning is allowed after opening these results.

These tests cover a small selected cool-star sample and idealized physical models.
They omit upstream SPOC losses and do not calibrate survey completeness or global
false-alarm probabilities. A pass warrants an exploratory pilot with full vetting,
not a discovery claim, a validated planet or methodological novelty.
