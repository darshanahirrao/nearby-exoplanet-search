"""Post-review fixed period-subdivision diagnostic, not independent validation."""

import argparse
from datetime import datetime, timezone
import hashlib
import json

import pandas as pd
from longbaseline import sector_split
from search import ROOT, event_checks


def compact(stats):
    return dict(
        n_events=stats["n_observed_events"],
        n_positive=stats["n_positive_events"],
        nominal_snr=stats["fixed_ephemeris_snr"],
    )


def check(tic, index, divisor):
    folder = ROOT / "results" / f"{tic}_longbaseline"
    result = json.loads((folder / "result.json").read_text())
    signal = result["signals"][index - 1]
    training, holdout = sector_split(pd.read_csv(folder / "lightcurve.csv.gz"))
    period, epoch, duration = (signal[k] for k in ("period_days", "epoch_btjd", "duration_days"))
    subdivisions, phase_classes = [], []
    for factor in range(1, 9):
        row = dict(factor=factor, period_days=period / factor)
        for name, df in [("training", training), ("holdout", holdout)]:
            row[name] = compact(event_checks(df, period / factor, epoch, duration))
        subdivisions.append(row)
    for residue in range(divisor):
        row = dict(residue=residue, epoch_btjd=epoch + residue * period / divisor)
        for name, df in [("training", training), ("holdout", holdout)]:
            row[name] = compact(event_checks(df, period, row["epoch_btjd"], duration))
        phase_classes.append(row)
    output = dict(
        tic=tic,
        checked_utc=datetime.now(timezone.utc).isoformat(),
        signal_index=index,
        trial_period_days=period,
        duration_days=duration,
        inspected_divisor=divisor,
        subdivisions=subdivisions,
        phase_classes=phase_classes,
        source_result_sha256=hashlib.sha256((folder / "result.json").read_bytes()).hexdigest(),
        scope="Fixed ephemeris and duration, with divisors 1 through 8. The chosen divisor has separate tests of each phase class. All are post-review diagnostics in already-inspected data, with nominal errors; no planet or unique astrophysical period is established.",
    )
    (folder / "subharmonic_checks.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(phase_classes, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tic", type=int, required=True)
    parser.add_argument("--signal", type=int, required=True)
    parser.add_argument("--divisor", type=int, choices=range(2, 9), required=True)
    args = parser.parse_args()
    check(args.tic, args.signal, args.divisor)
