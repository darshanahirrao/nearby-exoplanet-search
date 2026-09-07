# Cross-view prototype: useful spatial filtering, no demonstrated novel advantage

The first difference-map experiment preserved more injected target signals than
our simple aperture/positive-centroid diagnostic. A stricter ablation shows that
almost all of this improvement comes from spatial template fitting, a known
technique. The proposed frozen cross-view position has not demonstrated an
advantage sufficient for adoption.

| Evaluation | Injected target signals accepted | Displaced injections accepted | No-injection maps accepted |
| --- | ---: | ---: | ---: |
| Initial prototype, frozen position | 74 / 120 | 0 / 120 | 0 / 120 |
| Initial simple aperture/centroid comparator | 34 / 120 | 0 / 120 | 0 / 120 |
| Fresh ablation, frozen position | 181 / 300 | 0 / 300 | 0 / 300 |
| Same spatial filter, refit held-view position | 179 / 300 | 0 / 300 | 0 / 300 |
| Spatial filter always fixed to intended target | 180 / 300 | 11 / 300 | 0 / 300 |
| Fresh ablation, simple aperture/centroid comparator | 88 / 300 | 0 / 300 | 0 / 300 |

On paired target injections in the fresh ablation, freezing the position rescued
eight cases and lost six relative to refitting. The net gain of two cases does
not establish a meaningful improvement, and the six losses violate a strict
requirement to preserve every existing recovery. The current production search
and its acceptance decisions remain unchanged.

The real case studies predict displaced flux in TIC 448416124 and TIC 408232559,
consistent with the previous pixel review. They are already inspected examples;
neither is a new planet. TIC 282923395 remains below this prototype's training
threshold and its shorter variability has already been identified.

These tests add simplified Gaussian signals to real off-event difference maps.
The fitted and injected widths differ, but both shapes belong to related families.
Noise maps are reused, and some contain real stellar variability. Counts are not
independent-trial false-alarm probabilities, survey completeness, or raw-pixel
transit recovery. The baseline here is a deliberately simple localization
diagnostic; the ablation is essential to avoid attributing known matched-filter
benefits to the proposed cross-view component.

The initial design also mentions a detector-fixed alternative. This prototype
does not implement that branch: cutout-relative pixel coordinates cannot be
treated as fixed physical detector locations across cameras and CCDs. A proper
detector hypothesis would need full detector-coordinate metadata and comparable
instrument configurations.

The next research question is whether propagating the *uncertainty* of a
training position can improve a reserved-view prediction, especially with
non-Gaussian empirical pixel responses and closely blended sources. That is an
unimplemented hypothesis requiring fresh tests and a prior-art comparison.
No invention priority or scientific breakthrough is claimed by this result.

- [Frozen experiment protocol](../../../docs/EXPERIMENT_CROSS_VIEW.md)
- [Initial results and input hashes](summary.json)
- [Fresh ablation plan](ablation_plan.json)
- [All ablation results](ablation.json)

Reproduce with `python scripts/cross_view_experiment.py --cases 360` followed by
`python scripts/cross_view_ablation.py`, after retrieving the listed target-pixel
products and running the corresponding `pixel_vet.py` case studies.
