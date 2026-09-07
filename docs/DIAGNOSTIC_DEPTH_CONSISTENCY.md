# Training depth-consistency diagnostic

The repeated-event smoke guard failed: both methods preserved the control but
neither retained either missed injected signal. The 114 other planned new runs
remain unused. Inspect the same three exposed examples to locate the remaining
ranking failure; this is development, not independent validation.

Replay each of the first iteration's 128 existing fine fits at its saved period
using its original duration family. Require its duration, nominal BLS SNR and
local event statistics to match the saved fit before using the reconstruction.
Retain only the original training-eligible fits for ranking comparisons.

For event depths `d_i` and nominal errors `s_i`, fit their common weighted mean
and calculate `Q = sum((d_i-mean)**2/s_i**2)/(N-1)`. Divide the combined local
SNR and the leave-one-event-out SNR by `sqrt(max(1,Q))`. This never lowers the
nominal uncertainty. It penalizes a period whose apparent depth varies more
than its stated errors explain. It is related to established chi-square
consistency tests, including [Seader et al. (2013)](https://arxiv.org/abs/1302.7029).

Compare rankings on the already exposed first-iteration fits. Do not change
their eligibility or any holdout threshold. The calculation uses only training
flux; true injection timing labels the resulting ranks. Shared baseline windows,
residual variability and small event counts prevent interpreting these values
as calibrated significance, a formal chi-square null test or false-alarm rates.
