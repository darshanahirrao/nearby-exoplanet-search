# Apply training checks before allocating the two trial slots

This is a retrospective development ablation using the exact 45 injected cases
and five unmodified stars from the failed physical-duration experiment. Do not
call it fresh validation. Reuse the frozen original and three-pass harmonic
comparison results after verifying their source and result hashes.

Compare two new searches, both with the same three-pass lower-threshold harmonic
cleaning and the same physical coarse duration prior. Restore the exact original
fine-duration family and all original holdout checks. One comparison retains the
strongest seed each iteration with no early training qualification. The other
examines up to 64 distinct coarse period peaks per retained signal, in descending
coarse power. Neighboring periods within `2 * seed_duration / training_baseline`
in relative period are treated as the same peak for this shortlist.

The qualified variant only considers periods inside the nominal optimistic HZ,
then applies the original training event-count, one-event dominance, odd/even,
radius, HZ, duration and nominal-SNR checks after original timing refinement.
Rejected seeds neither consume a retained slot nor mask observations. Keep at
most two accepted signals and freeze them before the original held-sector checks.
All rejected training fits are retained as diagnostics. The helper has no access
to holdout flux. The coarse-only comparison isolates the effect of restoring
the original fine fit from the effect of early training qualification.

This uses more training refinements than the original pipeline. It is an
engineering search revision built from established BLS and vetting methods, not
an invention-priority claim. Limiting held-back evaluations to two fits does not
by itself calibrate the search false-alarm probability.

Execute 100 new runs. The development gate requires at least two additional
strict recoveries over the strongest of the original, three-pass harmonic and
coarse-only comparisons, no lost strict recovery from any comparison, no more
unflagged unmodified-star fits than the three-pass comparison, and no errors.
Keep the prior strict recovery definition and separately report all-screening
recoveries. A pass warrants a separately frozen new-star physical-transit
assessment; it does not retroactively activate the unused previous protocol.
