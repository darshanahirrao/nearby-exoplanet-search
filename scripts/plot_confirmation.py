"""Plot every star's strict recovery counts from the completed fixed experiment."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "reports/experiments/pipeline_confirmation"
    result = json.loads((folder / "results.json").read_text())
    plan = json.loads((folder / "plan.json").read_text())
    methods = ["production", "harmonic_three", "coarse_only", "qualified_seeds"]
    labels = [
        "Original",
        "Three-pass\nharmonic",
        "Physical\ncoarse seeds",
        "Early training\nqualification",
    ]
    colors = ["#4D6380", "#7B679C", "#CC8A27", "#268478"]
    tics = plan["selected_tics"]
    totals = [result["counts"][m]["strict"] for m in methods]
    per_star = np.array(
        [
            [
                sum(
                    r["strict"] is True
                    for r in result["rows"]
                    if r["method"] == m and r["tic"] == tic
                )
                for m in methods
            ]
            for tic in tics
        ]
    )
    assert np.array_equal(per_star.sum(axis=0), totals)
    fig = plt.figure(figsize=(11.6, 6.8), facecolor="white")
    grid = fig.add_gridspec(
        1, 2, left=0.075, right=0.98, bottom=0.24, top=0.77, width_ratios=[1, 1.05], wspace=0.42
    )
    left, right = fig.add_subplot(grid[0]), fig.add_subplot(grid[1])
    bars = left.bar(np.arange(4), totals, color=colors, width=0.64, zorder=3)
    for bar, value in zip(bars, totals):
        left.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.8,
            f"{value}/54",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color="#172A3B",
        )
    left.set_ylim(0, 59)
    left.set_yticks([0, 9, 18, 27, 36, 45, 54])
    left.set_ylabel("Strict recoveries", fontsize=11, color="#172A3B")
    left.set_xticks(range(4), labels, fontsize=9)
    left.grid(axis="y", color="#E4E9EE", zorder=0)
    left.spines[["top", "right"]].set_visible(False)
    left.set_title("All 54 modeled transits", fontsize=12, loc="left", pad=14)
    right.imshow(per_star, vmin=0, vmax=9, cmap="Blues", aspect="auto")
    for i in range(len(tics)):
        for j in range(4):
            value = int(per_star[i, j])
            right.text(
                j,
                i,
                f"{value}/9",
                ha="center",
                va="center",
                color="white" if value >= 6 else "#172A3B",
                fontsize=11,
                fontweight="bold",
            )
    right.set_yticks(range(len(tics)), [f"TIC {tic}" for tic in tics], fontsize=9)
    right.set_xticks(range(4), labels, fontsize=9)
    right.tick_params(length=0)
    for spine in right.spines.values():
        spine.set_visible(False)
    right.set_title("Every assessment star", fontsize=12, loc="left", pad=14)
    fig.text(
        0.075,
        0.94,
        "Independent injected-signal recovery",
        fontsize=21,
        weight="bold",
        color="#172A3B",
    )
    fig.text(
        0.075,
        0.885,
        "Six other stars · physical transit models added to real TESS light curves",
        fontsize=11,
        color="#4D6380",
    )
    passed = result["selected_for_exploratory_pilot"]
    decision = (
        f"Frozen gate selects {passed.replace('_', ' ')} for an exploratory pilot."
        if passed
        else "Neither revision passed the frozen confirmation gate."
    )
    fig.text(0.075, 0.12, decision, fontsize=11, weight="bold", color="#172A3B")
    fig.text(
        0.075,
        0.076,
        "216 injection runs shown; 24 unmodified-star runs are reported separately. Cases share stars and orbits.",
        fontsize=9,
        color="#4D6380",
    )
    fig.text(
        0.075,
        0.042,
        "Not a new planet, a completeness estimate, or a calibrated false-alarm probability. See the frozen plan and full results.",
        fontsize=9,
        color="#4D6380",
    )
    for suffix in ["png", "svg"]:
        path = folder / f"recovery.{suffix}"
        fig.savefig(path, dpi=180, facecolor="white")
        if suffix == "svg":
            path.write_text(
                "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
            )
    plt.close(fig)
    print(json.dumps(dict(strict_counts=dict(zip(methods, totals)), tics=tics)))


if __name__ == "__main__":
    main()
