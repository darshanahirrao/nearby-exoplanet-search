"""Per-event TESS difference-image diagnostics, not planet validation.

Compare the event image with a baseline interpolated between nearby pre-event and
post-event images. Weighted event stacks use nominal pixel errors. PRF fitting,
correlated-error calibration and updated astrometry remain necessary for precise
localization. Download target-pixel products before invoking this script.
"""

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm

ROOT = Path(__file__).resolve().parents[1]


def image_mean(cube, errors, mask):
    data = cube[mask]
    count = np.sum(np.isfinite(data), axis=0)
    mean = np.nansum(data, axis=0) / np.maximum(count, 1)
    variance = np.nansum(errors[mask] ** 2, axis=0) / np.maximum(count, 1) ** 2
    mean[count == 0] = np.nan
    variance[count == 0] = np.nan
    return mean, variance


def difference_stack(time, flux, errors, period, epoch, duration):
    differences, variances, centers = [], [], []
    cycles = np.unique(np.rint((time - epoch) / period).astype(int))
    window = min(period * 0.2, max(3 * duration, 0.3))
    for cycle in cycles:
        center = epoch + cycle * period
        dt = time - center
        inside = abs(dt) < duration / 2
        left = (dt < -duration * 0.8) & (dt > -window)
        right = (dt > duration * 0.8) & (dt < window)
        if min(inside.sum(), left.sum(), right.sum()) < 10:
            continue
        yin, ein = image_mean(flux, errors, inside)
        yleft, eleft = image_mean(flux, errors, left)
        yright, eright = image_mean(flux, errors, right)
        fraction = (np.mean(dt[inside]) - np.mean(dt[left])) / (
            np.mean(dt[right]) - np.mean(dt[left])
        )
        differences.append((1 - fraction) * yleft + fraction * yright - yin)
        variances.append((1 - fraction) ** 2 * eleft + fraction**2 * eright + ein)
        centers.append(float(center))
    if not differences:
        raise ValueError("No events have sufficient in-event and bracketing samples")
    differences, variances = np.array(differences), np.array(variances)
    good = np.isfinite(differences) & np.isfinite(variances) & (variances > 0)
    weights = np.zeros_like(variances)
    weights[good] = 1 / variances[good]
    total = weights.sum(axis=0)
    stack = np.divide(
        np.nansum(differences * weights, axis=0),
        total,
        out=np.full_like(total, np.nan),
        where=total > 0,
    )
    error = np.sqrt(np.divide(1, total, out=np.full_like(total, np.nan), where=total > 0))
    return stack, error, centers


def analyze(tic, period, epoch, duration):
    out = ROOT / "results" / f"{tic}_pixels"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    diverging = LinearSegmentedColormap.from_list("difference", ["#347299", "#ffffff", "#ad3b35"])
    for source in sorted((ROOT / "data/targetpixels" / str(tic)).glob("*_tp.fits")):
        with fits.open(source, memmap=False) as hdus:
            assert int(hdus[0].header["TICID"]) == tic
            header = hdus[0].header
            data = hdus[1].data
            keep = np.isfinite(data["TIME"]) & (data["QUALITY"] == 0)
            time = np.asarray(data["TIME"][keep], dtype=float)
            flux = np.asarray(data["FLUX"][keep], dtype=float)
            errors = np.asarray(data["FLUX_ERR"][keep], dtype=float)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                wcs = WCS(hdus[2].header)
            target_x, target_y = wcs.world_to_pixel_values(header["RA_OBJ"], header["DEC_OBJ"])
            sector = int(header["SECTOR"])
        difference, error, centers = difference_stack(time, flux, errors, period, epoch, duration)
        significance = difference / error
        peak_y, peak_x = np.unravel_index(np.nanargmax(significance), significance.shape)
        yy, xx = np.indices(difference.shape)
        # The local positive-flux centroid is a diagnostic, not a PRF-based source fit.
        core = (abs(xx - peak_x) <= 1) & (abs(yy - peak_y) <= 1)
        weights = np.where(core & np.isfinite(difference), np.maximum(difference, 0), 0)
        cx, cy = np.sum(xx * weights) / weights.sum(), np.sum(yy * weights) / weights.sum()
        sky = wcs.pixel_to_world_values(cx, cy)
        record = dict(
            sector=sector,
            events=len(centers),
            event_centers_btjd=centers,
            source=str(source.relative_to(ROOT)),
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            target_xy=[float(target_x), float(target_y)],
            positive_core_centroid_xy=[float(cx), float(cy)],
            positive_core_centroid_radec=list(map(float, sky)),
            offset_pixels=float(np.hypot(cx - target_x, cy - target_y)),
            peak_pixel_nominal_snr=float(significance[peak_y, peak_x]),
        )
        records.append(record)
        np.savez_compressed(
            out / f"sector_{sector}_images.npz", difference=difference, nominal_error=error
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mean = np.nanmedian(flux, axis=0)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
        positive = mean[np.isfinite(mean) & (mean > 0)]
        im = axes[0].imshow(
            mean,
            origin="lower",
            cmap="cividis",
            norm=LogNorm(vmin=max(0.01, np.percentile(positive, 5)), vmax=positive.max()),
        )
        fig.colorbar(im, ax=axes[0], label="Median flux [electrons/s]", shrink=0.75)
        limit = max(float(np.nanmax(abs(difference))), 1e-3)
        im = axes[1].imshow(difference, origin="lower", cmap=diverging, vmin=-limit, vmax=limit)
        fig.colorbar(im, ax=axes[1], label="Outside minus inside [electrons/s]", shrink=0.75)
        axes[0].set_title("Median image")
        axes[1].set_title(f"Difference image: {len(centers)} events")
        for ax in axes:
            ax.plot(target_x, target_y, "x", color="black", ms=10, mew=2, label="Target position")
            ax.plot(
                cx,
                cy,
                "o",
                mfc="none",
                mec="black",
                ms=13,
                mew=1.5,
                label="Positive difference core",
            )
            ax.set(xlabel="Pixel column", ylabel="Pixel row")
        axes[0].legend(loc="upper left", fontsize=8, framealpha=0.9)
        fig.suptitle(
            f"TIC {tic}, sector {sector}\nApproximate source offset {record['offset_pixels']:.2f} pixels; diagnostic only"
        )
        fig.savefig(out / f"sector_{sector}_difference.png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        print(tic, sector, record["offset_pixels"], record["peak_pixel_nominal_snr"], flush=True)
    result = dict(
        tic=tic,
        period_days=period,
        epoch_btjd=epoch,
        duration_days=duration,
        created_utc=datetime.now(timezone.utc).isoformat(),
        records=records,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations="Diagnostic pixel-error weighting ignores correlated errors. No precision PRF localization or planet validation. All available sectors may be used here after prior inspection; this is not untouched holdout evidence.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tic", type=int, required=True)
    parser.add_argument("--period", type=float, required=True)
    parser.add_argument("--epoch", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()
    analyze(args.tic, args.period, args.epoch, args.duration)
