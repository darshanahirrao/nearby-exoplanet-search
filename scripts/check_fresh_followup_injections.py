"""Post-follow-up sensitivity diagnostic; not a new blind recovery experiment."""

from datetime import datetime, timezone
import inspect
import json
from pathlib import Path

import pandas as pd

import followup_portfolio_trials as followup
from local_baseline import continuum_train
from multimode_cycle_experiment import weak
from realistic_injections import BOX_LINE, model_flux, total_duration
import search

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/vetting/fresh_sector_followup/injection_diagnostic"


def physical_loader(case, star):
    source = inspect.getsource(search.load_target)
    location = 'ROOT / "data/lightcurves" / str(tic)'
    assert source.count(location) == 1 and source.count(BOX_LINE) == 1
    source = source.replace(location, 'ROOT / "data/followup_lightcurves" / str(tic)')
    source = source.replace(BOX_LINE, "y = y * model_flux(t, physical_case, physical_star)")
    namespace = dict(vars(search), model_flux=model_flux, physical_case=case, physical_star=star)
    exec(compile(source, "<physical-followup-injection>", "exec"), namespace)
    return namespace["load_target"]


def main():
    original_plan = followup.verify_plan()
    OUT.mkdir(parents=True, exist_ok=True)
    queue_path = ROOT / "reports/experiments/portfolio/unmodified_review_queue.json"
    queue = {t["method"]: t["signal"] for t in json.loads(queue_path.read_text())["trials"]}
    files = [
        Path(__file__),
        ROOT / "scripts/realistic_injections.py",
        queue_path,
        followup.OUT / "plan.json",
        followup.OUT / "results.json",
        followup.OUT / "download_manifest.json",
    ]
    spec = dict(
        source_sha256={str(p.relative_to(ROOT)): followup.sha(p) for p in files},
        original_sources_sha256=original_plan["source_sha256"],
        cases=[
            dict(
                method=s["method"],
                **{
                    k: queue[s["method"]][k]
                    for k in [
                        "period_days",
                        "epoch_btjd",
                        "duration_days",
                        "depth",
                        "radius_earth_estimate",
                    ]
                },
            )
            for s in original_plan["signals"]
        ],
        models=["fitted_box", "circular_limb_darkened"],
        impact_parameter=0.0,
        limb_darkening=[0.3, 0.2],
        scope="Retrospective sensitivity diagnostic specified after the failed fresh-sector recurrence result. Inject the fitted box or a circular central transit of the originally estimated radius into fresh SPOC PDC before our processing. Keep the supplied period, epoch and fitted window for measurement. No period search, parameter tuning, or new discovery. Four selected model injections do not measure general completeness or upstream SPOC losses.",
    )
    plan_path = OUT / "plan.json"
    if plan_path.exists():
        prior = json.loads(plan_path.read_text())
        assert all(prior[k] == v for k, v in spec.items())
    else:
        followup.write(plan_path, dict(frozen_utc=datetime.now(timezone.utc).isoformat(), **spec))
    manifest = json.loads((followup.OUT / "download_manifest.json").read_text())
    for row in manifest["files"]:
        assert followup.sha(ROOT / row["path"]) == row["sha256"]
    star = pd.read_csv(ROOT / "data/catalogs/all_hz_targets.csv").set_index("TIC").loc[233738219]
    rows = []
    for signal in spec["cases"]:
        for model in spec["models"]:
            case = dict(
                period_days=signal["period_days"],
                epoch_btjd=signal["epoch_btjd"],
                radius_earth=signal["radius_earth_estimate"],
                impact_parameter=0.0,
                limb_darkening=spec["limb_darkening"],
            )
            loader = (
                followup.followup_loader() if model == "fitted_box" else physical_loader(case, star)
            )
            before, _ = loader(
                233738219,
                inject=dict(
                    period=signal["period_days"],
                    epoch=signal["epoch_btjd"],
                    duration=signal["duration_days"],
                    depth=signal["depth"],
                ),
            )
            after, _ = weak(before, star)
            original = search.event_checks(
                after, signal["period_days"], signal["epoch_btjd"], signal["duration_days"]
            )
            quadratic = continuum_train(
                after,
                signal["period_days"],
                signal["epoch_btjd"],
                signal["duration_days"],
                degree=2,
                width_scale=1.0,
            )
            row = dict(
                method=signal["method"],
                model=model,
                supplied_fit=signal,
                model_duration_days=signal["duration_days"]
                if model == "fitted_box"
                else total_duration(case, star),
                original=original,
                quadratic=quadratic,
                points=len(after),
            )
            followup.write(OUT / (signal["method"] + "_" + model + ".json"), row)
            compact = {k: v for k, v in row.items() if k not in ["original", "quadratic"]}
            compact.update(
                original={k: v for k, v in original.items() if k != "event_snr"},
                quadratic={k: v for k, v in quadratic.items() if k != "event_measurements"},
            )
            rows.append(compact)
            print(
                signal["method"],
                model,
                "original",
                original["fixed_ephemeris_snr"],
                "quadratic",
                quadratic["nominal_snr"],
                flush=True,
            )
    followup.write(
        OUT / "results.json",
        dict(
            completed_utc=datetime.now(timezone.utc).isoformat(),
            plan_sha256=followup.sha(plan_path),
            rows=rows,
        ),
    )


if __name__ == "__main__":
    main()
