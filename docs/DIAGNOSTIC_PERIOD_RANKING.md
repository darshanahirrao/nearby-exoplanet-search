# Selected-case period-ranking diagnostic

Before another recovery experiment, inspect two already identified missed-period
injections (TIC 233738219 orbit 2, one Earth radius; TIC 229614158 orbit 0, one
Earth radius) and one previously tested control (TIC 328799321 orbit 1, one Earth
radius). This is selected-case development with known injected truth, not
independent recovery, a quality gate, a new planet or proof of method novelty.

Reconstruct the same physical injections, three-pass harmonic subtraction,
training sectors and physical-duration coarse BLS grid. Retain up to 4,096
distinct peaks inside the nominal HZ, using the existing training helper's
resolution exclusion. For each fixed coarse ephemeris, measure event depths
against the same nearby baseline windows as the original event check. Prefix
sums accelerate these measurements without changing their nominal errors.

Compare global BLS ordering with local combined event SNR and with the minimum
combined SNR remaining after any one event is omitted, also capped at the full
combined SNR. At least three sampled events are required for the latter. This
asks whether a period has support beyond its strongest individual event.
No held-sector flux is read by the period-ranking calculation. Injection truth
labels matching peaks only after selection and scoring.

This limited diagnostic tests whether the candidate list contains the missed
signal and whether either local ranking moves it upward. It does not run the
full fine fit or establish a blind strict recovery. The larger seed budget and
the local baseline are separate changes that must be controlled in any later
paired comparison. Shared baseline windows can correlate the event errors.

Prior art: Kepler already used robust event-consistency statistics and chi-square
discriminators; see [Seader et al. (2013)](https://arxiv.org/abs/1302.7029) and
the [NASA Exoplanet Archive definitions](https://exoplanetarchive.ipac.caltech.edu/docs/API_tce_columns.html).
The project-specific leave-one-event-out ordering is an unvalidated hypothesis,
not a claimed invention of transit-consistency testing.
