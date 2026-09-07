"""Apply the frozen coverage pipeline to the remaining 45 inventory stars."""

import argparse
import fcntl
import inspect
import json
import os
from pathlib import Path

import coverage_pilot as pilot

ROOT = pilot.ROOT
REPORT = ROOT / "reports/coverage_continuation"


def prepare():
    # Verify the completed first batch before selecting the remainder.
    pilot.REPORT = ROOT / "reports/coverage_pilot"
    original_plan = pilot.verify_plan()
    audit = json.loads((pilot.REPORT / "audit.json").read_text())
    results = json.loads((pilot.REPORT / "results.json").read_text())
    assert audit["passed"] and not audit["failures"]
    assert audit["results_sha256"] == pilot.sha(pilot.REPORT / "results.json")
    assert audit["exporter_sha256"] == pilot.sha(ROOT / "scripts/export_coverage_pilot.py")
    assert results["status"] == "finished" and not results["errors"]
    assert results["completed"] == 20 and results["unflagged"] == 0
    pilot.REPORT = REPORT

    # Only selection, output report and provenance change; download, loading,
    # search, screening and receipt checks are the original functions.
    source = inspect.getsource(pilot.prepare)
    changes = [
        ('inventory["rows"][:20], 1', 'inventory["rows"][20:], 21'),
        (
            'len(targets) == 20 and sum(len(r["unused_products"]) for r in targets) == 390',
            'len(targets) == 45 and sum(len(r["unused_products"]) for r in targets) == 887',
        ),
        ('ROOT / "docs/COVERAGE_PILOT.md"', 'ROOT / "docs/COVERAGE_CONTINUATION.md"'),
        (
            "Path(__file__),",
            'Path(__file__),\n        ROOT / "scripts/coverage_pilot.py",\n'
            '        ROOT / "docs/COVERAGE_PILOT.md",\n'
            '        ROOT / "scripts/export_coverage_pilot.py",\n'
            '        ROOT / "reports/coverage_pilot/plan.json",\n'
            '        ROOT / "reports/coverage_pilot/audit.json",\n'
            '        ROOT / "reports/coverage_pilot/results.json",',
        ),
        (
            "First 20 ranked rows of the published unused-coverage inventory, unchanged.",
            "All remaining ranked rows 21 through 65 of the published unused-coverage inventory, unchanged.",
        ),
    ]
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError("Expected exactly one preparation substitution: " + old)
        source = source.replace(old, new)
    namespace = dict(vars(pilot), REPORT=REPORT, __file__=str(Path(__file__)))
    exec(compile(source, "<remaining-coverage-preparation>", "exec"), namespace)
    namespace["prepare"]()
    plan = pilot.verify_plan()
    selected = {row["tic"] for row in plan["targets"]}
    assert len(selected) == 45
    assert selected.isdisjoint(row["tic"] for row in original_plan["targets"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["prepare", "download", "run"])
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.workers < 1 or args.workers * 2 > (os.cpu_count() or 1):
        parser.error("Workers must fit two BLS threads each within the CPU count")
    (ROOT / "logs").mkdir(exist_ok=True)
    with (ROOT / "logs/coverage_continuation.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.operation == "prepare":
            prepare()
        else:
            pilot.REPORT = REPORT
            if args.operation == "download":
                pilot.download()
            else:
                pilot.run(args.workers)
