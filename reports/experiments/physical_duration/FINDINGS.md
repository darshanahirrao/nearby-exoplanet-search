# Early duration prior: development gate failed

All 150 method runs completed without errors on 45 fresh injected cases and five
unmodified stars. The early duration prior is not adopted by the production
search. The prepared six-star physical-transit assessment remains unexecuted.

| Method | Period recovered / 45 | Strict recovery / 45 | Strict and every screening check | Unflagged unmodified-star fits |
| --- | ---: | ---: | ---: | ---: |
| Original single harmonic pass | 24 | 19 | 19 | 1 |
| Up to three lower-threshold harmonic passes | 25 | 20 | 20 | 0 |
| Same three-pass cleaning, early duration prior | 26 | 20 | 20 | 0 |

The new method tied the stronger comparison and lost one strict recovery, so it
missed both the required gain of two and the no-loss condition. It gained one
strict case in Wolf 1069 at an injected 23.1447-day period and 0.8 Earth radii.
It still recovered the correct period of the lost strict case, TIC 232970271 at
4.84026 days and 0.8 Earth radii. However, the fitted duration changed from about
0.029 to 0.032 days, and the fixed-ephemeris held-sector SNR changed from 5.189 to
4.692, below the fixed threshold of 5. No holdout threshold was relaxed.

These are finite synthetic tests on previously studied stars, with box shapes
that favor BLS. They do not establish completeness, a calibrated false-alarm
probability, a new astrophysical object or a new algorithm. Physical duration
priors are established practice, including in
[Hippke and Heller (2019)](https://arxiv.org/abs/1901.02015).

The original campaign nevertheless has a clear limitation: 1,665 of 1,816
combined-season fits had the long-duration flag, and 779 targets had both fits
flagged this way. These are retrospective counts, not evidence for hidden
planets. See [source and count hashes](../search_bottleneck/campaign_duration_counts.json).

Reproduce with `python scripts/physical_duration_experiment.py --workers 3`.
The [plan](plan.json) records the exact cases and source hashes;
[results](results.json) retain every paired outcome. The physical adapter replaces
the legacy duration-family field in the unchanged search's config, as explicitly
recorded in the plan. All other search checks are unchanged.
