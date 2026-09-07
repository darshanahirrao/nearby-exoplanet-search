# Revised pilot

**All 100 stars finished: 200 trial fits, zero unflagged fits, zero execution
errors, and no planet candidate.** The run finished on 2026-09-07 at 09:19 UTC,
having started at 09:02 UTC. It used `coarse_only`, selected by the completed
[240-run confirmation](../experiments/pipeline_confirmation/FINDINGS.md),
and has passed the real TOI-700 d prerequisite. All 1,213 telescope input
files matched their recorded hashes before execution. No new planet is claimed.

The [target selection](../../provenance/revised_pilot_selection.json) was frozen
before examining these stars with either revision. The [execution plan](plan.json)
freezes the selected method, its code and prerequisites. The [execution protocol](../../docs/REVISED_PILOT_EXECUTION.md)
describes inputs, output locations and review requirements.

The original 1,031-star campaign remains unchanged. These 100 stars were already
searched, so they contribute zero additional distinct stars. Every trial failed
the held-sector evidence requirement: 183 failed the SNR threshold, and 17 had
insufficient sampled held-sector events. The review queue is empty.

| Same 100 stars | Original combined-season search | Revised pilot |
| --- | ---: | ---: |
| Trial fits | 200 | 200 |
| Unflagged fits | 0 | 0 |
| Long relative to a circular transit | 200 | 11 |
| Low nominal training SNR | 29 | 84 |
| Not recovered in held sectors | 185 | 183 |
| Insufficient held-sector events | 11 | 17 |

Flags overlap. The revision changed which periods were retained, so these are
counts of different fits on the same inputs and sector split. Removing many
implausibly long fits did not produce convincing held-sector evidence. This is
not a completeness, false-alarm or planet-occurrence measurement.

The [complete target receipts](results.json), [all 200 fits and per-event
measurements](trials.json), [summary and review queue](summary.json), and
[final audit](audit.json) are public. The audit rechecked all 1,213 telescope
files, frozen source hashes, all four output files per target, fitted ephemerides,
sector separation and the original comparison's sector splits. It passed.

The separate [known-timing diagnostic](../experiments/confirmation_diagnostic/FINDINGS.md)
identifies missed injected signals as a further development question. No
parameters or thresholds were changed during this pilot.

For local output progress, use `python scripts/progress.py --experiments-only`.
This reads saved files; a partial output alone does not prove that a process is
currently running. The complete live log is `logs/revised_pilot.log`.
