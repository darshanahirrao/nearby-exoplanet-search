"""Preserve analysis-relevant public catalogue fields with checked restoration.

ExoFOP free-text fields are omitted. Numeric strings used by the analysis retain
their original spelling. Original-download and derived-file hashes are distinct.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "provenance" / "catalogues"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def create():
    manifest = json.loads((ROOT / "data/catalogs/manifest.json").read_text())
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    records = []
    for source in manifest:
        path = ROOT / source["file"]
        original = path.read_bytes()
        if sha(original) != source["sha256"]:
            raise ValueError(f"Source hash changed: {path.name}")
        data = original
        columns = None
        if path.name in ["exofop_toi.csv", "exofop_ctoi.csv"]:
            columns = [
                "TIC ID",
                "TOI" if path.name == "exofop_toi.csv" else "CTOI",
                "Period (days)",
            ]
            if path.name == "exofop_toi.csv":
                columns += ["Epoch (BJD)", "Duration (hours)"]
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(
                stream, fieldnames=columns, lineterminator="\n", extrasaction="ignore"
            )
            writer.writeheader()
            for row in csv.DictReader(io.StringIO(original.decode("utf-8-sig"))):
                writer.writerow(row)
            data = stream.getvalue().encode()
        packed = gzip.compress(data, mtime=0)
        name = path.name + ".gz"
        (SNAPSHOT / name).write_bytes(packed)
        records.append(
            dict(
                name=path.name,
                archive=name,
                source_url=source["url"],
                original_sha256=source["sha256"],
                stored_sha256=sha(data),
                gzip_sha256=sha(packed),
                columns=columns,
            )
        )
    result = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        files=records,
        description="Public catalogue snapshot. ExoFOP contains only fields used in the numerical pipeline; all other files preserve original bytes.",
    )
    (SNAPSHOT / "manifest.json").write_text(json.dumps(result, indent=2))
    print("Stored", len(records), "catalogue inputs")


def restore(destination):
    records = json.loads((SNAPSHOT / "manifest.json").read_text())["files"]
    verified = []
    destination = Path(destination)
    # Validate the complete restore before writing any files.
    for record in records:
        name, archive = record["name"], record["archive"]
        if Path(name).name != name or Path(archive).name != archive:
            raise ValueError("Invalid snapshot file name")
        packed = (SNAPSHOT / archive).read_bytes()
        if sha(packed) != record["gzip_sha256"]:
            raise ValueError(f"Compressed hash mismatch: {archive}")
        data = gzip.decompress(packed)
        if sha(data) != record["stored_sha256"]:
            raise ValueError(f"Input hash mismatch: {name}")
        out = destination / name
        if out.exists() and out.read_bytes() != data:
            raise ValueError(f"Existing input differs: {out}. Use a clean directory.")
        verified.append((out, data))
    destination.mkdir(parents=True, exist_ok=True)
    for out, data in verified:
        out.write_bytes(data)
    print("Restored", len(verified), "verified inputs to", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["create", "restore"])
    parser.add_argument("--destination", type=Path, default=ROOT / "data/catalogs")
    args = parser.parse_args()
    create() if args.operation == "create" else restore(args.destination)
