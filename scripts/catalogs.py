"""Download reproducible public catalogue snapshots and rank initial targets."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, json
import numpy as np
import pandas as pd
import requests
from astropy.io import ascii

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "data/catalogs"
CAT.mkdir(parents=True, exist_ok=True)


def fetch(item):
    name, url = item
    p = CAT / name
    if not p.exists():
        r = requests.get(url, timeout=(15, 90))
        r.raise_for_status()
        p.write_bytes(r.content)
    return {
        "file": str(p.relative_to(ROOT)),
        "url": url,
        "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "retrieved_or_reused_utc": datetime.now(timezone.utc).isoformat(),
    }


def main():
    base = "https://cdsarc.cds.unistra.fr/ftp/J/AJ/161/233/"
    sources = [("ReadMe", base + "ReadMe")] + [
        (f"table{i}.dat", base + f"table{i}.dat") for i in [3, 5, 6]
    ]
    sources += [
        (
            "exofop_toi.csv",
            "https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv",
        ),
        (
            "exofop_ctoi.csv",
            "https://exofop.ipac.caltech.edu/tess/download_ctoi.php?sort=ctoi&output=csv",
        ),
    ]
    query = "select pl_name,hostname,tic_id,gaia_dr2_id,gaia_dr3_id,ra,dec,pl_orbper,pl_tranmid,pl_trandur,pl_rade,pl_insol,st_rad,st_mass,st_teff,sy_dist from pscomppars"
    sources.append(
        (
            "confirmed_planets.csv",
            "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?"
            + requests.compat.urlencode({"query": query, "format": "csv"}),
        )
    )
    manifest = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(fetch, s): s for s in sources}
        for j, s in jobs.items():
            try:
                v = j.result()
                manifest.append(v)
                print(s[0], v["bytes"], flush=True)
            except Exception as e:
                manifest.append({"file": s[0], "url": s[1], "error": repr(e)})
                print(s[0], repr(e), flush=True)
    (CAT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    tables = []
    for num in [3, 5]:
        t = ascii.read(
            CAT / f"table{num}.dat", readme=str(CAT / "ReadMe"), format="cds"
        ).to_pandas()
        t["catalogue_table"] = num
        tables.append(t)
    stars = pd.concat(tables).drop_duplicates("TIC").copy()
    stars["TIC"] = stars.TIC.astype("int64")
    # Recompute luminosity from R and Teff to avoid rounding a faint star's L to zero.
    stars["luminosity_recomputed"] = stars.Rad**2 * (stars.Teff / 5772.0) ** 4
    stars["earth_depth_ppm"] = (0.0091577 / stars.Rad) ** 2 * 1e6
    stars["earth_period_days"] = 365.256 * np.sqrt(stars.luminosity_recomputed**1.5 / stars.Mass)
    toi = pd.read_csv(CAT / "exofop_toi.csv")
    tid = pd.to_numeric(toi["TIC ID"], errors="coerce").dropna().astype("int64")
    stars["known_toi_host"] = stars.TIC.isin(tid)
    try:
        ct = pd.read_csv(CAT / "exofop_ctoi.csv")
        ctcol = next(c for c in ct.columns if c.lower().replace(" ", "") in ["ticid", "tic"])
        stars["known_ctoi_host"] = stars.TIC.isin(
            pd.to_numeric(ct[ctcol], errors="coerce").dropna().astype("int64")
        )
    except Exception:
        stars["known_ctoi_host"] = False
    # Broad feasible pool; observed photometric noise will replace this crude ranking.
    eligible = stars[
        (stars.Rad.between(0.1, 0.65))
        & (stars.Mass > 0)
        & stars.Teff.between(2600, 4500)
        & (stars.Dist <= 100)
        & (stars.Tmag <= 14)
        & stars.earth_period_days.between(3, 90)
    ].copy()
    eligible["priority_score"] = (
        eligible.earth_depth_ppm
        * 10 ** (-0.2 * (eligible.Tmag - 10))
        * np.sqrt(30 / eligible.earth_period_days)
    )
    eligible["priority_score"] *= np.where(eligible.Dist <= 35, 1.25, 1)
    eligible = eligible.sort_values("priority_score", ascending=False)
    stars.to_csv(CAT / "all_hz_targets.csv", index=False)
    eligible.to_csv(CAT / "ranked_targets.csv", index=False)
    print(
        "all",
        len(stars),
        "eligible",
        len(eligible),
        "without_TOI",
        sum(~eligible.known_toi_host),
        flush=True,
    )
    print(
        eligible[
            [
                "TIC",
                "Tmag",
                "Rad",
                "Teff",
                "Dist",
                "earth_period_days",
                "earth_depth_ppm",
                "known_toi_host",
                "known_ctoi_host",
            ]
        ]
        .head(30)
        .to_string(index=False),
        flush=True,
    )


if __name__ == "__main__":
    main()
