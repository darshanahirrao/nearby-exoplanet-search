"""Verify downloaded FITS identities and record byte hashes for reproducibility."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]


def inspect(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with fits.open(path, memmap=True) as hdus:
        primary, time_header = hdus[0].header, hdus[1].header
        tic = int(primary["TICID"])
        timesys = time_header.get("TIMESYS")
        bjdref = time_header.get("BJDREFI", 0) + time_header.get("BJDREFF", 0)
        valid = tic == int(path.parent.name) and timesys == "TDB" and bjdref == 2457000
        return dict(
            path=str(path.relative_to(ROOT)),
            tic=tic,
            sector=int(primary["SECTOR"]),
            bytes=path.stat().st_size,
            sha256=digest,
            time_system=timesys,
            bjd_reference=bjdref,
            identity_and_time_valid=valid,
        )


def main():
    paths = sorted((ROOT / "data/lightcurves").glob("*/*_lc.fits"))
    paths += sorted((ROOT / "data/targetpixels").glob("*/*_tp.fits"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(inspect, paths))
    if not rows:
        raise ValueError("No FITS inputs found")
    with (ROOT / "provenance/telescope_inputs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    result = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        files=len(rows),
        distinct_tics=len({r["tic"] for r in rows}),
        bytes=sum(r["bytes"] for r in rows),
        identity_or_time_failures=[r for r in rows if not r["identity_and_time_valid"]],
        scope="Every downloaded light-curve and target-pixel FITS input present at this checkpoint. Includes calibration data and files unused by a particular search variant.",
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (ROOT / "reports/input_audit.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if result["identity_or_time_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
