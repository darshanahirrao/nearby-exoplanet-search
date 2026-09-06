"""Retrieve explicitly selected public SPOC target-pixel sectors for vetting."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from astropy.io import fits
import lightkurve as lk
import requests

ROOT = Path(__file__).resolve().parents[1]


def download(tic, sectors):
    sectors = sorted(set(sectors))
    result = lk.search_targetpixelfile(
        f"TIC {tic}", mission="TESS", author="SPOC", exptime=120, sector=sectors
    )
    if not len(result):
        raise ValueError("No matching SPOC target-pixel products")
    folder = ROOT / "data/targetpixels" / str(tic)
    folder.mkdir(parents=True, exist_ok=True)
    result.table.write(folder / "products.ecsv", overwrite=True)
    rows = []
    with requests.Session() as session:
        for product in result.table:
            filename = str(product["productFilename"])
            if Path(filename).name != filename:
                raise ValueError("Product name must be a plain filename")
            path = folder / filename
            uri = str(product["dataURI"])
            url = "https://mast.stsci.edu/api/v0.1/Download/file"
            if not path.exists():
                response = session.get(url, params={"uri": uri}, timeout=(15, 100))
                response.raise_for_status()
                if not response.content.startswith(b"SIMPLE"):
                    raise ValueError("Download is not a FITS primary HDU")
                temporary = path.with_suffix(".part")
                temporary.write_bytes(response.content)
                with fits.open(temporary, memmap=True) as hdus:
                    if int(hdus[0].header["TICID"]) != tic:
                        raise ValueError("Downloaded TIC identity mismatch")
                temporary.replace(path)
            with fits.open(path, memmap=True) as hdus:
                sector = int(hdus[0].header["SECTOR"])
                if int(hdus[0].header["TICID"]) != tic or sector not in sectors:
                    raise ValueError("Unexpected target or observing sector")
            rows.append(
                dict(
                    path=str(path.relative_to(ROOT)),
                    sector=sector,
                    uri=uri,
                    bytes=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            )
            print(tic, sector, "downloaded", path.stat().st_size, flush=True)
    manifest = dict(
        tic=tic,
        retrieved_utc=datetime.now(timezone.utc).isoformat(),
        requested_sectors=sectors,
        missing_sectors=sorted(set(sectors) - {r["sector"] for r in rows}),
        files=rows,
    )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if manifest["missing_sectors"]:
        raise ValueError(f"Missing sectors: {manifest['missing_sectors']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tic", type=int, required=True)
    parser.add_argument("--sectors", type=int, nargs="+", required=True)
    args = parser.parse_args()
    download(args.tic, args.sectors)
