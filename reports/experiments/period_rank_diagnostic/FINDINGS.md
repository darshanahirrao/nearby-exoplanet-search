# Local repeated-event ranking: selected-case diagnostic

Requiring support after the strongest event is omitted moves both missed
injected transits upward in the same fixed list of 4,096 coarse seeds. Neither
becomes the highest-ranked seed, and these ranks do not constitute recovery.

| Exposed injected case | Global BLS rank | Local event SNR rank | Leave-one-event-out rank |
| --- | ---: | ---: | ---: |
| TIC 233738219, orbit 2, one Earth radius | 1,316 | 571 | 84 |
| TIC 229614158, orbit 0, one Earth radius | 2,108 | 401 | 76 |
| TIC 328799321, orbit 1, one Earth radius; control | 1 | 1 | 1 |

The fast prefix-sum implementation matches the existing local event checks on
gapped, heteroskedastic data. A synthetic single-dip test gives a strong total
SNR but zero evidence after that dip is removed, as intended. These software
checks validate the calculation, not its scientific superiority.

The [protocol](../../../docs/DIAGNOSTIC_PERIOD_RANKING.md), [plan](plan.json),
[summary](results.json), and complete per-case seed files retain the calculation.
This motivated a 128-refinement development budget. The [subsequent full-fitting
smoke test](../repeated_events/FINDINGS.md) did not recover either missed signal
when only two fits were retained. No discovery or method novelty is established.
