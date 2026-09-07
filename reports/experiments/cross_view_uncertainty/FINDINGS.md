# Uncertainty-weighted prediction did not preserve discrimination quality

The second prototype retained a distribution of source positions fitted to
training images and averaged the corresponding templates in the reserved view.
The resulting weights are normalized profile likelihoods, not calibrated source
probabilities. Thresholds and seed were frozen before evaluation.

| Injection shape | Method | Target signals accepted | Displaced signals accepted | No-injection maps accepted |
| --- | --- | ---: | ---: | ---: |
| Gaussian | Uncertainty-weighted prediction | 169 / 300 | 12 / 300 | 0 / 300 |
| Gaussian | Same filter, refit reserved view | 165 / 300 | 6 / 300 | 0 / 300 |
| Empirical positive deficit core | Uncertainty-weighted prediction | 158 / 300 | 12 / 300 | 0 / 300 |
| Empirical positive deficit core | Same filter, refit reserved view | 156 / 300 | 11 / 300 | 0 / 300 |

Together this is six additional target recoveries and seven additional displaced
acceptances. Paired comparisons include 19 target cases recovered only by the new
variant and 13 recovered only by the comparison method. The variant therefore
fails the project's requirement to improve performance while preserving current
quality. It is not adopted.

This stress test includes separations from 0.25 to 3 nominal TESS pixels, including
close blends. Earlier tests started at 0.75 pixels, so their zero-contamination
counts must not be compared as if the target populations were identical.
The empirical injection shapes are shifted positive cores of observed deficit
images; they include response mismatch and noise and are not calibrated PRFs.
The tests reuse finite real off-event maps. They do not establish survey
completeness, astrophysical false-positive rates, or sensitivity on raw pixels.

An offline check verifies that reversing reserved-view flux leaves the fitted
weights and predicted template unchanged, while reversing its measured score.
This confirms the intended data separation; it does not rescue the unfavorable
performance result or establish novelty.

- [Frozen plan](plan.json)
- [All 1,800 cases and comparison scores](results.json)
- [Prototype](../../../scripts/cross_view_uncertainty.py)

Reproduce with `python scripts/cross_view_uncertainty.py` using the target-pixel
inputs prepared for the first cross-view experiment.
