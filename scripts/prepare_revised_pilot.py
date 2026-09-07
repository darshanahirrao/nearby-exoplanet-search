"""Freeze metadata-only pilot targets; this script never searches their flux."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "provenance/revised_pilot_selection.json"
    files = [
        "scripts/prepare_revised_pilot.py",
        "docs/REVISED_SEARCH_PILOT.md",
        "data/catalogs/all_hz_targets.csv",
        "reports/tables/targets.csv",
        "provenance/telescope_inputs.csv",
        "reports/experiments/pipeline_confirmation/plan.json",
    ]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    if out.exists():
        old = json.loads(out.read_text())
        if old["source_sha256"] != hashes:
            raise ValueError("Preserve the frozen pilot selection")
        print(json.dumps(dict(state="already_frozen", selected=len(old["targets"]))))
        return
    stars = pd.read_csv(ROOT / files[2]).set_index("TIC")
    targets = pd.read_csv(ROOT / files[3]).set_index("tic")
    inputs = pd.read_csv(ROOT / files[4])
    confirmation = json.loads((ROOT / files[5]).read_text())
    excluded = sorted(
        set(
            [
                232970271,
                352617553,
                378527773,
                219223742,
                397098265,
                150428135,
                448416124,
                408232559,
                282923395,
                22535327,
            ]
            + confirmation["selected_tics"]
        )
    )
    data = stars.join(targets[["sectors"]], how="inner")
    data = data[
        (data.sectors >= 6)
        & data.Tmag.between(8, 14)
        & data.Rad.between(0.1, 0.4)
        & (data.earth_period_days <= 20)
        & ~data.known_toi_host
        & ~data.known_ctoi_host
        & ~data.index.isin(excluded)
    ].copy()
    data["ranking_proxy"] = (
        data.earth_depth_ppm
        * 10 ** (-0.2 * (data.Tmag - 10))
        * np.sqrt(27 * data.sectors / data.earth_period_days)
    )
    data = data.reset_index(names="tic").sort_values(
        ["ranking_proxy", "tic"], ascending=[False, True]
    )
    selected = data.head(100)
    if len(selected) != 100 or not np.all(np.isfinite(selected.ranking_proxy)):
        raise ValueError("Insufficient eligible pilot targets")
    rows = []
    for rank, row in enumerate(selected.itertuples(index=False), 1):
        current = inputs[(inputs.tic == row.tic) & inputs.path.str.startswith("data/lightcurves/")]
        if len(current) < row.sectors or not current.identity_and_time_valid.all():
            raise ValueError(f"Incomplete audited telescope inputs for {row.tic}")
        if not all((ROOT / p).exists() for p in current.path):
            raise ValueError(f"Missing telescope inputs for {row.tic}")
        rows.append(
            dict(
                rank=rank,
                tic=int(row.tic),
                tmag=float(row.Tmag),
                radius_solar=float(row.Rad),
                mass_solar=float(row.Mass),
                earth_period_days=float(row.earth_period_days),
                sectors=int(row.sectors),
                ranking_proxy=float(row.ranking_proxy),
                telescope_inputs=current[["path", "sector", "bytes", "sha256"]].to_dict("records"),
            )
        )
    plan = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=hashes,
        eligible_count=len(data),
        excluded_controls=excluded,
        targets=rows,
        state="selection_only_not_executed",
        claims="Metadata-only selection for a conditional exploratory reanalysis. No new target score, planet or discovery.",
    )
    out.write_text(json.dumps(plan, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                selected=len(rows),
                eligible=len(data),
                telescope_files=sum(len(r["telescope_inputs"]) for r in rows),
                top_tics=[r["tic"] for r in rows[:5]],
            )
        )
    )


if __name__ == "__main__":
    main()
