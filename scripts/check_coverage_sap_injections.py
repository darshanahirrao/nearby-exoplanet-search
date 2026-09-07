"""Retrospective fixed-timing SAP controls with header-based dilution."""

from datetime import datetime, timezone
import inspect
from importlib.metadata import version
import json

import numpy as np
import pandas as pd

from local_baseline import continuum_train
from multimode_cycle_experiment import weak
from realistic_injections import BOX_LINE, model_flux, total_duration
import search
from coverage_pilot import ROOT, sha, save

TIC = 142086813
OUT = ROOT / "reports/vetting/coverage_142086813"


def main():
    result_path = ROOT / "results/142086813_coverage_pilot/result.json"
    result = json.loads(result_path.read_text())
    signal = result["signals"][1]
    star = pd.Series(result["star"])
    diagnostics = json.loads((OUT / "diagnostics.json").read_text())
    period, epoch, duration = (signal[k] for k in ["period_days", "epoch_btjd", "duration_days"])
    case = dict(
        period_days=period,
        epoch_btjd=epoch,
        radius_earth=signal["radius_earth_estimate"],
        impact_parameter=0,
        limb_darkening=[0.3, 0.2],
    )
    records, input_hashes = [], {}
    for shape in ["zero", "box", "physical"]:
        source = inspect.getsource(search.load_target)
        assert source.count(BOX_LINE) == 1
        expression = {
            "zero": "np.ones(len(t))",
            "box": '1 - inject["depth"] * (np.abs(phase) < inject["duration"] / 2)',
            "physical": "model_flux(t, case, star)",
        }[shape]
        source = source.replace(
            BOX_LINE,
            'crowd = float(h[1].header["CROWDSAP"])\n'
            "                assert np.isfinite(crowd) and 0 < crowd <= 1\n"
            f"                y = y * (1 - crowd * (1 - ({expression})))",
        )
        frames, metadata = [], []
        for directory in ["data/lightcurves", "data/coverage_lightcurves"]:
            path_source = source.replace(
                'ROOT / "data/lightcurves" / str(tic)', f'ROOT / "{directory}" / str(tic)'
            )
            ns = dict(vars(search), model_flux=model_flux, case=case, star=star)
            exec(compile(path_source, "<diluted-SAP-injection>", "exec"), ns)
            frame, meta = ns["load_target"](
                TIC,
                flux_column="SAP_FLUX",
                inject=dict(period=period, epoch=epoch, duration=duration, depth=signal["depth"]),
            )
            frames.append(frame)
            metadata.extend(meta)
        assert set(frames[0].sector).isdisjoint(frames[1].sector)
        original = pd.concat(frames, ignore_index=True).sort_values("time")
        assert not original.time.duplicated().any()
        cleaned, _ = weak(original, star)
        parts = {}
        for stage, frame in [("before", original), ("after", cleaned)]:
            parts[stage] = {}
            for part in ["training", "holdout"]:
                data = frame.loc[frame.sector.isin(result[part + "_sectors"])]
                measured = search.event_checks(data, period, epoch, duration)
                if shape == "zero":
                    reference = diagnostics["measurements"]["target_SAP_" + stage][part]["original"]
                    assert np.isclose(
                        measured["fixed_ephemeris_snr"], reference["fixed_ephemeris_snr"], atol=1e-7
                    )
                parts[stage][part] = dict(
                    original=measured,
                    quadratic=continuum_train(data, period, epoch, duration, 2, 1),
                )
        for item in metadata:
            input_hashes[item["file"]] = sha(ROOT / item["file"])
        records.append(
            dict(
                shape=shape,
                parts=parts,
                sector_crowding=[
                    dict(sector=m["sector"], crowdsap=m["crowdsap"]) for m in metadata
                ],
            )
        )
    record = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        tic=TIC,
        result_sha256=sha(result_path),
        diagnostic_sha256=sha(OUT / "diagnostics.json"),
        script_sha256=sha(ROOT / "scripts/check_coverage_sap_injections.py"),
        source_sha256={
            name: sha(ROOT / name)
            for name in [
                "scripts/realistic_injections.py",
                "scripts/local_baseline.py",
                "scripts/multimode_cycle_experiment.py",
                "scripts/cycle_excluded.py",
                "scripts/variability.py",
                "scripts/search.py",
                "scripts/physics.py",
                "requirements-experiments.txt",
                "requirements.lock.txt",
            ]
        },
        package_versions={name: version(name) for name in ["batman-package", "numpy", "astropy"]},
        input_sha256=input_hashes,
        physical_case=case,
        physical_duration_days=total_duration(case, star),
        measurement_duration_days=duration,
        records=records,
        scope="Retrospective controls after inspecting the failed SAP diagnostic. Inject a zero model, the fitted box, and a central circular limb-darkened model into archived SAP before project processing; multiply modeled target flux loss by each sector's CROWDSAP. Header crowding is an estimate, not independently validated dilution. Fixed original ephemeris and measurement duration, no blind search, no selection or gate change, no population completeness or general transit-preservation claim.",
    )
    save(OUT / "sap_injection_diagnostic.json", record)
    for row in records:
        print(
            row["shape"],
            {
                stage: {
                    part: (d["original"]["fixed_ephemeris_snr"], d["quadratic"]["nominal_snr"])
                    for part, d in parts.items()
                }
                for stage, parts in row["parts"].items()
            },
        )


if __name__ == "__main__":
    main()
