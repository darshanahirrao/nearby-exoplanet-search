"""Audit and publish every fit from the completed bounded revised pilot."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from revised_pilot import checked_cache, prepare, sha

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/revised_pilot"


def main():
    state = json.loads((REPORT / "results.json").read_text())
    if state["status"] != "finished" or state["completed"] != 100 or state["errors"]:
        raise ValueError("The entire frozen pilot must finish before final export")
    spec, plan_hash = prepare()
    rows = {r["tic"]: r for r in state["rows"]}
    if set(rows) != set(spec["selected_tics"]) or len(state["rows"]) != 100:
        raise ValueError("Wrong pilot result set")
    trials = []
    prior_trials = []
    original_hashes = {}
    for tic in spec["selected_tics"]:
        receipt = checked_cache(tic, plan_hash)
        if receipt != rows[tic]:
            raise ValueError(f"Pilot receipt differs from final index: {tic}")
        result = json.loads((ROOT / receipt["result_path"]).read_text())
        for index, signal in enumerate(result["signals"], 1):
            trials.append(
                dict(
                    tic=tic,
                    signal_index=index,
                    result_path=receipt["result_path"],
                    result_sha256=receipt["output_sha256"]["result.json"],
                    frozen_training_sha256=receipt["output_sha256"]["frozen_training.json"],
                    training_sectors=result["training_sectors"],
                    holdout_sectors=result["holdout_sectors"],
                    star={k: result["star"][k] for k in ["Mass", "Rad", "Teff", "Tmag"]},
                    signal=signal,
                )
            )
        path = ROOT / "results" / f"{tic}_longbaseline" / "result.json"
        prior = json.loads(path.read_text())
        if (
            prior["training_sectors"] != result["training_sectors"]
            or prior["holdout_sectors"] != result["holdout_sectors"]
        ):
            raise ValueError(f"Original comparison uses different sector split: {tic}")
        original_hashes[str(path.relative_to(ROOT))] = sha(path)
        prior_trials.extend(prior["signals"])
    if len(trials) != sum(r["fits"] for r in rows.values()):
        raise ValueError("Trial count mismatch")
    queue = [
        {k: r[k] for k in ["tic", "signal_index", "result_path", "result_sha256"]}
        for r in trials
        if not r["signal"]["screening_flags"]
    ]

    def tally(signals):
        return dict(
            trial_fits=len(signals),
            unflagged=sum(not s["screening_flags"] for s in signals),
            flags=dict(sorted(Counter(f for s in signals for f in s["screening_flags"]).items())),
        )

    summary = dict(
        exported_utc=datetime.now(timezone.utc).isoformat(),
        distinct_reanalysed_stars=100,
        additional_distinct_stars=0,
        pilot=tally([r["signal"] for r in trials]),
        original_same_targets=tally(prior_trials),
        queue=queue,
        scope="All fits retained. Flag counts overlap and do not measure completeness or false-alarm rates. Every unflagged fit needs astrophysical review.",
    )
    audit = dict(
        passed=True,
        completed_target_receipts=100,
        telescope_files_rechecked=spec["telescope_files_checked"],
        plan_sha256=plan_hash,
        results_sha256=sha(REPORT / "results.json"),
        exporter_sha256=sha(Path(__file__)),
        original_comparison_sha256=original_hashes,
        checks="All frozen source and input hashes, exact target set, all four files per receipt, unchanged fitted ephemerides, disjoint sectors, same original comparison sector split, and fit counts.",
    )
    for name, value in [("trials.json", trials), ("summary.json", summary), ("audit.json", audit)]:
        (REPORT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
