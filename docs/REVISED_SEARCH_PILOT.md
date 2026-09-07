# Conditional pilot of a complete pipeline revision

Prepare 100 existing survey targets before examining their flux with either
revision. Do not execute until `pipeline_confirmation` selects a revision under
its frozen rules and the same revision retains the known roughly 37.424-day
TOI-700 signal under the real-signal control's strict checks. If either condition
fails, leave this selection unused and preserve the outcome.

Stay within the six-star assessment's main catalogue domain: at least six usable
sectors, TESS magnitude 8–14, stellar radius 0.1–0.4 solar radii, Earth-irradiation
period at most 20 days, and no known TOI/CTOI host in the frozen catalogue. Exclude
all development, pixel and independent-assessment controls listed in the
selection script. Rank eligible stars by catalogue Earth-transit depth times
`10**(-0.2 * (Tmag - 10)) * sqrt(27 * sectors / Earth_period)`, breaking ties by
TIC. This is a ranking proxy, not a measured SNR or completeness estimate.

The selection uses only catalogue properties and observation counts, not new
period scores, held-sector transit depths or the confirmation outcomes. Freeze
the top 100 identities, all input references and source hashes. The preceding
survey already inspected these stars, so the pilot is an exploratory reanalysis,
not an independent population sample. Reanalyzing them must not increase the
reported count of distinct searched stars.

When authorized by the frozen scientific conditions, use the selected revision
unchanged. Retain both successful and failed target records, all training-seed
diagnostics, frozen ephemerides and held-sector checks. Cross-match every
unflagged signal with the frozen catalogues, then review event shapes, alternate
extractions, variability aliases, source pixels and current catalogues before
promoting anything. A repeatable dimming or unflagged fit alone is not a verified
planet, habitable world, new object or naming entitlement.
