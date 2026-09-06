"""Targeted diagnostic after rapid residual oscillations were identified.

Applies at most two further sector-local variability fits, then repeats the
unchanged combined-season search. This post-review experiment is not a blind
survey and does not establish completeness or a false-alarm probability.
"""

import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from search import ROOT, known_matches
from variability import clean_variability
from longbaseline import search_combined


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tic", type=int, required=True)
    args = parser.parse_args()
    source = ROOT / "results" / f"{args.tic}_known_residual"
    out = ROOT / "results" / f"{args.tic}_targeted_multimode"
    out.mkdir(exist_ok=True)
    prior = json.loads((source / "result.json").read_text())
    star = pd.Series(prior["star"])
    curve = pd.read_csv(source / "lightcurve.csv.gz")
    models = []
    for extra_pass in range(1, 3):
        curve, records = clean_variability(curve, star)
        models.append(dict(extra_pass=extra_pass, records=records))
        if not any(r["applied"] for r in records):
            break
    curve.to_csv(out / "lightcurve.csv.gz", index=False)
    result = search_combined(curve, star, out)
    for signal in result["signals"]:
        signal["known_matches"] = known_matches(args.tic, signal["period_days"])
        if signal["known_matches"]:
            signal["screening_flags"].append("known_period_or_harmonic_requires_review")
    result.update(
        tic=args.tic,
        additional_variability_models=models,
        source=str(source.relative_to(ROOT)),
        source_sha256=hashlib.sha256((source / "lightcurve.csv.gz").read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        claim="Targeted post-review diagnostic, not a discovery claim or independent survey.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2))
    for s in result["signals"]:
        print(
            s["period_days"],
            s["nominal_training_snr"],
            s["holdout"]["fixed_ephemeris_snr"],
            s["screening_flags"],
            flush=True,
        )


if __name__ == "__main__":
    main()
