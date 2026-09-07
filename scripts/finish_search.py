"""Finish bounded local search stages, then stop for scientific review.

No automatic publication, planet validation, or public discovery claim.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--wait-pids", type=int, nargs="*", default=[])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--parallel-threads", type=int, default=1)
    args = parser.parse_args()
    if args.campaign != Path(args.campaign).name:
        raise ValueError("campaign must be a plain name")
    state_file = ROOT / "logs/final_stages.json"
    state = dict(started_utc=datetime.now(timezone.utc).isoformat(), campaign=args.campaign)

    def checkpoint(stage):
        state.update(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat())
        state_file.write_text(json.dumps(state, indent=2))
        print(stage, state["updated_utc"], flush=True)

    def run_stage(script, *arguments):
        checkpoint(script)
        with (ROOT / "logs" / ("final_" + Path(script).stem + ".log")).open("w") as stream:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script), *map(str, arguments)],
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=True,
            )

    try:
        checkpoint("waiting_for_bounded_campaign")
        deadline = time.monotonic() + 4 * 3600
        while time.monotonic() < deadline:
            try:
                campaign = json.loads((ROOT / "logs" / (args.campaign + ".json")).read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(10)
                continue
            if campaign["stage"] == "error":
                raise RuntimeError(campaign.get("error", "Campaign failed"))
            if campaign["stage"] == "finished_pending_human_or_agent_review":
                break
            time.sleep(10)
        else:
            raise TimeoutError("Bounded campaign did not finish within four hours")
        checkpoint("waiting_for_prior_local_searches")
        for pid in args.wait_pids:
            while time.monotonic() < deadline:
                process = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True
                )
                if process.returncode or "python" not in process.stdout.lower():
                    break
                time.sleep(10)
            else:
                raise TimeoutError(f"Prior process {pid} did not finish")
        run_stage("variability.py", "--all-screened", "--workers", args.workers)
        if args.parallel_threads > 1:
            run_stage(
                "accelerated_longbaseline.py",
                "--all-screened",
                "--workers",
                args.workers,
                "--threads",
                args.parallel_threads,
            )
        else:
            run_stage("longbaseline.py", "--all-screened", "--workers", args.workers)
        run_stage("audit_inputs.py")
        run_stage("summarize.py")
        checkpoint("finished_pending_scientific_review")
    except Exception as exc:
        state["error"] = repr(exc)
        checkpoint("error")
        raise


if __name__ == "__main__":
    main()
