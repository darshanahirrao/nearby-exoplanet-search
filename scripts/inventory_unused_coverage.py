"""Rank opportunities for deeper archival coverage; this does not search periods."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from astropy.table import Table
import numpy as np
import pandas as pd

from search import bin_series, robust_sigma

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stars_path = ROOT / "data/catalogs/all_hz_targets.csv"
    confirmed_path = ROOT / "data/catalogs/confirmed_planets.csv"
    targets_path = ROOT / "reports/tables/targets.csv"
    stars = pd.read_csv(stars_path).set_index("TIC")
    searched = set(pd.read_csv(targets_path).tic.astype(int))
    confirmed = pd.read_csv(confirmed_path)
    known = set(
        pd.to_numeric(
            confirmed.tic_id.astype(str).str.replace("TIC ", "", regex=False), errors="coerce"
        )
        .dropna()
        .astype(int)
    )
    rows, errors = [], []
    for tic in sorted(searched):
        if tic not in stars.index:
            continue
        star = stars.loc[tic]
        if tic in known or star.known_toi_host or star.known_ctoi_host or tic == 233738219:
            continue
        catalog = ROOT / f"data/products/{tic}.ecsv"
        curve = ROOT / f"results/{tic}/lightcurve.csv.gz"
        if not catalog.exists() or not curve.exists():
            continue
        try:
            old_files = sorted((ROOT / "data/lightcurves" / str(tic)).glob("*_lc.fits"))
            old = {int(re.search(r"-s(\d{4})-", p.name).group(1)) for p in old_files}
            table = Table.read(catalog)
            products = [
                dict(
                    sector=int(p["sequence_number"]),
                    filename=str(p["productFilename"]),
                    uri=str(p["dataURI"]),
                )
                for p in table
                if str(p["author"]) == "SPOC" and float(p["exptime"]) == 120
            ]
            available = {p["sector"] for p in products}
            fresh = available - old
            if len(old) < 6 or len(fresh) < 12:
                continue
            frame = pd.read_csv(curve)
            _, flux, _ = bin_series(
                frame.time.to_numpy(), frame.flux.to_numpy(), frame.err.to_numpy(), step=2 / 24
            )
            noise = float(robust_sigma(flux) * 1e6)
            if len(flux) < 50 or not np.isfinite(noise) or noise <= 0:
                raise ValueError("Insufficient or invalid two-hour noise estimate")
            period, depth = float(star.earth_period_days), float(star.earth_depth_ppm)
            proxy = depth / noise * np.sqrt(27 * len(available) / period)
            rows.append(
                dict(
                    tic=tic,
                    tmag=float(star.Tmag),
                    radius_solar=float(star.Rad),
                    mass_solar=float(star.Mass),
                    distance_pc=float(star.Dist),
                    earth_period_days=period,
                    earth_depth_ppm=depth,
                    old_sectors=sorted(old),
                    unused_sectors=sorted(fresh),
                    available_sectors=sorted(available),
                    old_two_hour_scatter_ppm=noise,
                    old_two_hour_bins=len(flux),
                    coverage_sqrt_ratio=float(np.sqrt(len(available) / len(old))),
                    ranking_proxy=float(proxy),
                    unused_products=sorted(
                        [p for p in products if p["sector"] in fresh], key=lambda p: p["sector"]
                    ),
                    catalogue_source=str(catalog.relative_to(ROOT)),
                    catalogue_sha256=sha(catalog),
                    noise_source=str(curve.relative_to(ROOT)),
                    noise_source_sha256=sha(curve),
                )
            )
        except Exception as exc:
            errors.append(dict(tic=tic, error=repr(exc)))
    rows.sort(key=lambda r: (-r["ranking_proxy"], r["tic"]))
    out = ROOT / "reports/unused_coverage"
    out.mkdir(exist_ok=True)
    report = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256={
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                Path(__file__),
                ROOT / "scripts/search.py",
                stars_path,
                confirmed_path,
                targets_path,
            ]
        },
        eligibility="Previously searched main-campaign star with at least six existing sectors and at least twelve unused 120-second SPOC sectors in its cached product table; exclude known TOI, CTOI and confirmed-planet hosts and the just-reviewed TIC 233738219.",
        ranking="Earth-depth proxy divided by robust scatter of weighted two-hour bins in the already examined, original detrended flux before harmonic filtering, times sqrt(27 * total available sectors / Earth-irradiation period). Higher rank favors quieter, deeply observed small stars.",
        scope="Planning inventory only, using metadata and old flux. No new flux downloaded or period search performed. Coverage ratios and ranking proxies are not calibrated sensitivity gains. No method adoption, novelty or planet claim.",
        eligible_count=len(rows),
        errors=errors,
        rows=rows,
    )
    (out / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                eligible=len(rows),
                errors=errors,
                top=[
                    {
                        k: r[k]
                        for k in [
                            "tic",
                            "old_two_hour_scatter_ppm",
                            "coverage_sqrt_ratio",
                            "ranking_proxy",
                            "unused_sectors",
                        ]
                    }
                    for r in rows[:12]
                ],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
