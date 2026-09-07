# Why were physical injections missed?

This is a retrospective diagnostic using the known injected period, epoch and
total transit duration. It does not count as blind recovery or change any
completed experiment's decision. All 54 cases from the selected revision were
reprocessed using their original physical model and fixed harmonic filter.

| Diagnostic at the known injected timing | Before harmonic subtraction | After harmonic subtraction |
| --- | ---: | ---: |
| At least three sampled training events and two held-sector events | 54/54 | 54/54 |
| Event-depth SNR at least 7 in training and 5 in held sectors | 9/54 | 11/54 |
| Above those reference SNRs but not a strict blind recovery | 4 | 5 |

All modeled total durations are between about 38 and 138 minutes. The minimum
sample-count rule at the exact true duration is therefore not the reason for
the missing recoveries in these cases. Most cases fall below one of the
reference event-SNR thresholds even when their true timings are supplied.
Those statistics include residual real stellar/instrumental structure and the
pipeline's retained error floor; they are not a calibrated detectability limit.

After harmonic cleaning, four of the five above-reference misses retained
other periods: three injections on TIC 233738219 and one on TIC 229614158.
The fifth, on TIC 357509778, retains a period near the injected value but fails
the frozen holdout check. Its score using the supplied true ephemeris crosses
the reference threshold. This identifies both period-selection failures and
sensitivity to the fitted timing/duration near a cutoff.

The event-depth statistic and total-duration window differ from the fitted BLS
training score and window. Consequently the 11 diagnostic cases are not a
denominator for the seven blind strict recoveries: only six cases overlap.
For example, one blind strict recovery has true-window held-sector SNR 4.935.
Do not infer that exactly four more planets are recoverable, or use the supplied
timings to retune the ongoing 100-star pilot.

The [manifest](plan.json), [all 54 measurements](results.json), and
[diagnostic code](../../../scripts/diagnose_confirmation.py) preserve the
calculation. This identifies research questions; it establishes no new
planet, new method, completeness estimate or false-alarm probability.
