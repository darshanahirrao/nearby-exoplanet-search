# Unused archival coverage: planning inventory

The inventory identifies 65 previously searched stars with at least twelve unused 120-second SPOC sectors and no recorded TOI, CTOI or confirmed-planet host match in the project catalogue snapshot. The metadata and old-light-curve scan completed with zero errors.

The first 20 ranked stars have 390 unused sector products. Their original data contain 360 sectors. No new flux for these stars has been downloaded or searched by this inventory.

Ranking uses the originally examined two-hour flux scatter, the catalogue Earth-radius transit-depth proxy and the available sector count. It favors low variability relative to an Earth-sized signal and substantial unused coverage. The score is a planning proxy, not a detection probability or measured improvement. It does not establish that any selected system contains a transiting planet.

| Rank | TIC | Old sectors | Unused sectors | Old two-hour scatter [ppm] | Earth-radius depth proxy [ppm] |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 176935123 | 18 | 22 | 599 | 6807 |
| 2 | 149423103 | 18 | 24 | 407 | 2770 |
| 3 | 289589923 | 18 | 22 | 325 | 2251 |
| 4 | 349374765 | 18 | 22 | 148 | 1290 |
| 5 | 232607684 | 18 | 12 | 1361 | 6686 |
| 6 | 441803471 | 18 | 21 | 378 | 2275 |
| 7 | 441721594 | 18 | 22 | 287 | 1831 |
| 8 | 219775481 | 18 | 12 | 870 | 4534 |
| 9 | 141154638 | 18 | 23 | 1814 | 5824 |
| 10 | 32050414 | 18 | 17 | 1800 | 6023 |
| 11 | 219884888 | 18 | 23 | 357 | 1831 |
| 12 | 232612888 | 18 | 12 | 687 | 3196 |

[The inventory](inventory.json) includes all eligible targets, unused product identifiers, original-light-curve hashes and catalogue hashes. Reproduce with `python scripts/inventory_unused_coverage.py`.

A subsequent bounded survey requires its own frozen selection and data plan. The intended comparison uses the `coarse_only` revision that passed the prior complete-pipeline comparison and real TOI-700 d control. The failed enlarged-shortlist variants remain unused. This inventory itself starts no survey and does not increase the distinct-star count.
