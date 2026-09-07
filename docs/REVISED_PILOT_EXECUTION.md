# Execution of the revised 100-star pilot

The metadata selection in `provenance/revised_pilot_selection.json` predates
the confirmation outcome and is unchanged. The completed 240-run comparison
selects `coarse_only` under its frozen rules. It has seven strict recoveries
against four for each legacy comparison, no lost legacy strict recovery, gains
on three stars, and no unflagged fit in the six unmodified-star diagnostics.
The selected revision also retains the real TOI-700 d control strictly.

The runner refuses to proceed unless both scientific conditions and the
confirmation artifact audit pass. It verifies the original source hashes,
control outputs, exact input sets, and all 1,213 selected FITS byte hashes before
execution. The execution manifest additionally freezes the runner and all
prerequisite outputs. Re-running the command checks completed receipts and
preserves them; an interrupted incomplete target requires inspection.

Load unmodified PDCSAP data using the same original loader, including its
quality cut, ten-minute binning, median trend and retained error floor. Apply
the same three-pass harmonic filter and unchanged `coarse_only` search as the
confirmation: physical duration constraints only for coarse seed selection,
original fine fitting, two trial slots, whole-sector holdout and all original
screening thresholds. Catalogue matching happens after holdout evaluation.
No transit injection is used. Preserve raw and filtered local light curves,
all seed diagnostics, frozen training fits, final flags and file receipts in
`results/<TIC>_revised_pilot/`.

Run from the repository root after reproducing all prerequisites:

```sh
python scripts/audit_confirmation.py
python scripts/revised_pilot.py              # verify and freeze without searching
python scripts/revised_pilot.py --run --workers 3
```

Each numerical worker uses the existing two-thread BLS adapter. This is a
bounded exploratory reanalysis of 100 previously searched stars. It does not
increase the 1,031 distinct-star count. Every unflagged fit remains pending
astrophysical review until event shapes, alternate extractions, aliases, source
pixels and current catalogues are examined. The limited injection gain is not
a survey completeness estimate, calibrated false-alarm probability, novel
method, discovered planet or established habitability.
