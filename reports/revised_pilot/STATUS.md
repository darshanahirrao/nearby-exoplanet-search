# Revised pilot

The 100-star numerical search started on 2026-09-07 at 09:02 UTC. It uses
`coarse_only`, selected by the completed
[240-run confirmation](../experiments/pipeline_confirmation/FINDINGS.md),
and has passed the real TOI-700 d prerequisite. All 1,213 telescope input
files matched their recorded hashes before execution. No new planet is claimed.

The [target selection](../../provenance/revised_pilot_selection.json) was frozen
before examining these stars with either revision. The [execution plan](plan.json)
freezes the selected method, its code and prerequisites. The [execution protocol](../../docs/REVISED_PILOT_EXECUTION.md)
describes inputs, output locations and review requirements.

The original 1,031-star campaign remains unchanged. These 100 stars were already
searched, so they contribute zero additional distinct stars. Completion counts
and all accepted or rejected fit records will be exported after the run; every
unflagged fit requires further astrophysical review.

For local output progress, use `python scripts/progress.py --experiments-only`.
This reads saved files; a partial output alone does not prove that a process is
currently running. The complete live log is `logs/revised_pilot.log`.
