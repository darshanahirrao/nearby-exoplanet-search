# Target-response constraints increased short-timescale noise

This prototype fits pixel weights on the first half of each TESS sector. It
minimizes a regularized covariance objective while keeping the response to 81
modeled target footprints between 0.97 and 1.03. The weights are saved before
evaluating the second half. The comparison is the fixed SPOC aperture, normalized
to unit response for the central reference footprint.

All eight optimizations satisfied the constraints. However, short-timescale
scatter increased in every reserved half, by approximately 15–33%. Total robust
scatter fell only in the three sectors of TIC 448416124, where displaced-source
variability was already identified. It increased in the other five sectors.

| TIC | Sector | Total scatter / aperture | Adjacent-difference scatter / aperture |
| --- | ---: | ---: | ---: |
| 448416124 | 9 | 0.847 | 1.154 |
| 448416124 | 36 | 0.589 | 1.327 |
| 448416124 | 63 | 0.816 | 1.227 |
| 408232559 | 5 | 1.077 | 1.166 |
| 408232559 | 32 | 1.158 | 1.204 |
| 408232559 | 6 | 1.181 | 1.177 |
| 282923395 | 14 | 1.120 | 1.205 |
| 282923395 | 48 | 1.022 | 1.184 |

Lower ratios are better for these scatter metrics. These quantities are measured
in the reference-normalized extraction units; they are not transit recovery rates.
The experiment does not establish a sensitivity improvement and is **not adopted**.

The preservation bound applies only to the finite set of modeled footprints.
Random footprints between grid points reached a response of about 1.035, exceeding
the upper grid constraint. Real point-spread functions and wider position/width
errors need not obey either bound. Pixel-box injections agreed numerically with
the frozen linear operator's predicted response; this verifies the extraction
calculation, not blind recovery of an unknown transit period.

This is a small, exploratory study of eight already inspected sectors from three
fields, not an independent survey validation. Pixel validity selection uses the
whole sector, while the covariance and weights use only training-half flux.
Constrained minimum-variance estimation and optimal photometry have prior art;
no invention priority is established. Related pixel-level methods include
[CPM](https://arxiv.org/abs/1508.01853) and
[modified CPM](https://arxiv.org/abs/1805.05734), which address different objectives.

- [Frozen protocol](../../../docs/EXPERIMENT_PROTECTED_PIXELS.md)
- [Frozen settings and code hash](plan.json)
- [All measurements, response draws and constraint checks](results.json)
- [Prototype](../../../scripts/protected_pixel_experiment.py)

Reproduce with `python scripts/protected_pixel_experiment.py` after preparing the
target-pixel inputs for the cross-view experiment. No new production search was
run with these weights.
