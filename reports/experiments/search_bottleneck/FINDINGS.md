# Search bottleneck diagnostic

This post-result investigation uses two previously missed synthetic signals in
Wolf 1069. It does not count as blind recovery or an independent benchmark.
The period neighborhoods are selected using the injected truth.

Both had measurable ten-minute training and held-sector signals. The full
production search nevertheless missed them even with eight retained fits.
Its strongest broad seed was about 0.248 days long at a 29.367-day period,
versus a predicted central circular duration of about 0.070 days. Such seeds
consume the fitted-peak budget before the later physical vetting rejects them.

| Known injected case | Harmonic passes | Coarse duration family | Grid points stronger than injected-period neighborhood |
| --- | ---: | --- | ---: |
| 13.382 days, 0.6 Earth radii | 1 | Production | 12,103 |
| Same | 3 | Production | 6,973 |
| Same | 3 | 0.02–0.09 days | 845 |
| 9.886 days, 0.8 Earth radii | 1 | Production | 1,037 |
| Same | 3 | Production | 60 |
| Same | 3 | 0.02–0.09 days | 0 |

These are grid-point counts, not independent competing planets, probabilities
or significance estimates. The period neighborhoods use the known injection;
a zero count means the unrestricted period search peaks there in this diagnostic.
No full recovery claim is made from the coarse scan alone.

Physical duration priors are established practice, including in
[Hippke and Heller's TLS method](https://arxiv.org/abs/1901.02015) and its
[implementation](https://github.com/hippke/tls). Fixing this weakness in our
pipeline would be an engineering and sensitivity improvement, not sufficient
evidence of a new detection algorithm.

The weaker case is still not strongest. Extra cleaning alone and duration
restriction alone are insufficient for the stronger case. Their combination
motivates a fresh paired raw-injection benchmark against both the original
search and a harmonic comparison with the same cleaning budget.

The saved forced-coarse event scores are not directly comparable to the
ten-minute scores: the unchanged event checker requires at least three in-event
samples, which short transits can fail after thirty-minute binning. This does not
mean a zero-flux signal. BLS scores use a different sample-level likelihood.

See [diagnostic data](diagnostic.json) and
[executable diagnostic](../../../scripts/search_bottleneck_diagnostic.py).
