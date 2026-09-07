# TIC 142086813: not promoted as a credible planet lead

The 64.8279185569-day second fit passed the unchanged initial screens. Its
[original fit and measurements](diagnostics.json) remain preserved, alongside
this separate [review disposition](disposition.json). No discovery is claimed.

The nominal held-sector score is 5.52 across four events, falling to 1.76 when
cycle 14 is omitted. All three quadratic-baseline held-sector scores are below
five (3.51, 4.13, 4.30). [Every observed event](events.png) is shown: strong
training windows include broad trends, missing local coverage and a gap.
The corresponding [SAP and companion-extraction folds](folds.png) do not
corroborate a repeated isolated dip. SAP scores after project filtering are
−0.72 in training and −1.81 in held sectors. PDC and SAP share pixels; this is
a processing comparison, not independent telescope confirmation.

[Retrospective SAP controls](sap_injection_diagnostic.json) inject the fitted
box and a central circular physical transit before our processing, scaled by
each sector's estimated CROWDSAP dilution (0.461–0.748). This use follows the
[TESS crowding definition](https://heasarc.gsfc.nasa.gov/docs/tess/UnderstandingCrowdingv2.html).
After filtering, held-sector original/quadratic scores are 8.12/8.31 for the
box and 4.90/5.29 for the physical model. The physical original score is slightly
below five; we do not claim that every control passes the original screen.
Before filtering its corresponding scores are 5.69/5.81. These selected,
fixed-timing controls demonstrate measurable injected signals, not blind
recovery, general completeness or perfectly known dilution.

Exact-TIC TOI, CTOI and NASA confirmed-planet checks returned no matches;
that does not establish novelty. [SIMBAD identifies this star as L 32-8](https://simbad.u-strasbg.fr/simbad/sim-id?Ident=L+32-8).
The combined evidence is insufficient to promote this trial to a credible
planet lead. The unique cause is unresolved; other planets are not excluded.

The [review audit](audit.json) passes 883 provenance and arithmetic checks.
The second-fit training mask is replayed to reproduce the original saved score;
subsequent event diagnostics restore all samples. Reproduce with
`python scripts/vet_coverage_trial.py`,
`python scripts/check_coverage_sap_injections.py`, and
`python scripts/audit_coverage_vetting.py`. Catalogue responses can change.
