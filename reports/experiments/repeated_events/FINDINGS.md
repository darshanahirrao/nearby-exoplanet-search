# Two-fit repeated-event smoke guard failed

All six smoke runs completed without errors. Both fixed rankings preserve the
previously recovered TIC 328799321 injection under all checks; neither recovers
either missed injection under all checks. The smoke guard fails for both, so
the remaining 114 planned new runs were not executed. There is no full 120-run
comparison result or development-adoption decision.

| Method | Control recovered under all checks | Missed examples recovered / 2 |
| --- | ---: | ---: |
| Local total event SNR | Yes | 0 |
| Leave-one-event-out SNR | Yes | 0 |

Both methods examine 4,096 coarse seeds and refine up to 128 before retaining
each of two fits. In the TIC 233738219 example, the correct period is refined
near 15.775225 days and passes every training check, but other fits rank higher.
Thus a higher coarse rank alone does not resolve the detection problem.

See the [fixed protocol](../../../docs/EXPERIMENT_REPEATED_EVENTS.md),
[source/case manifest](plan.json), and [all six outcomes](smoke_results.json).
These exposed cases are development data. The failed guard and unused runs
remain preserved while other hypotheses are investigated.
