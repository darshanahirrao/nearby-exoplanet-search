"""Prototype frozen-position prediction across TESS observing geometries.

Difference-map experiment only; not an end-to-end transit search or a calibrated
planet-validation probability. The baseline search is never modified.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.special import erf
from pixel_vet import difference_stack

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    448416124: (9, 36, 63),
    408232559: (5, 32, 6),
    282923395: (14, 48),
}
PIXEL_ARCSEC = 21.0
GRID = (
    np.array([(x, y) for x in np.arange(-3, 3.01, 0.25) for y in np.arange(-3, 3.01, 0.25)])
    * PIXEL_ARCSEC
)


def kernel(shape, xy, widths=(0.8, 0.8)):
    """Pixel-integrated Gaussian; intentionally not a precision TESS PRF."""
    yy, xx = np.indices(shape)
    value = np.ones(shape)
    for coordinate, center, width in [(xx, xy[0], widths[0]), (yy, xy[1], widths[1])]:
        value *= 0.5 * (
            erf((coordinate + 0.5 - center) / (2**0.5 * width))
            - erf((coordinate - 0.5 - center) / (2**0.5 * width))
        )
    return value


class Frame:
    def __init__(self, data):
        self.data = data
        self.error = data["error"]
        self.target = data["target"]
        self.inverse = np.linalg.inv(data["sky_matrix"])
        self.shape = self.error.shape
        yy, xx = np.indices(self.shape)
        self.good = np.isfinite(self.error) & (self.error > 0)
        # Remove a spatial plane as a shared background nuisance for both methods.
        design = (
            np.stack([np.ones(self.shape), xx, yy], axis=-1)[self.good]
            / self.error[self.good, None]
        )
        self.q = np.linalg.qr(design, mode="reduced")[0]
        model = np.array([self.whiten(kernel(self.shape, self.xy(offset))) for offset in GRID])
        norm = np.linalg.norm(model, axis=1)
        self.models = model / norm[:, None]
        self.target_index = int(np.argmin(np.linalg.norm(GRID, axis=1)))

    def xy(self, offset):
        return self.target + self.inverse @ np.asarray(offset)

    def whiten(self, image):
        value = np.asarray(image)[self.good] / self.error[self.good]
        return value - self.q @ (self.q.T @ value)

    def scores(self, image):
        return self.models @ self.whiten(image)

    def baseline(self, image):
        valid = self.good & np.isfinite(image)
        snr = np.where(valid, image / self.error, -np.inf)
        py, px = np.unravel_index(np.argmax(snr), self.shape)
        yy, xx = np.indices(self.shape)
        core = valid & (abs(xx - px) <= 1) & (abs(yy - py) <= 1)
        weight = np.where(core, np.maximum(image, 0), 0)
        if weight.sum() == 0:
            distance = np.inf
        else:
            center = np.array([(xx * weight).sum(), (yy * weight).sum()]) / weight.sum()
            distance = np.linalg.norm(center - self.target)
        # Project a fixed SPOC aperture through the same background nuisance.
        aperture = self.data["aperture"].astype(float)
        # In whitened coordinates, summing physical flux weights by error.
        direction = aperture[self.good] * self.error[self.good]
        direction -= self.q @ (self.q.T @ direction)
        norm = np.linalg.norm(direction)
        score = float(direction @ self.whiten(image) / norm) if norm > 0 else 0.0
        return score, float(distance)


def evaluate(frames, images):
    train_scores = [f.scores(d) for f, d in zip(frames[:-1], images[:-1])]
    training_likelihood = np.sum([np.maximum(z, 0) ** 2 for z in train_scores], axis=0)
    best = int(np.argmax(training_likelihood))
    train_snr = float(np.sqrt(training_likelihood[best]))
    # No fit of held-view position: only score the frozen training prediction.
    holdout_snr = float(frames[-1].scores(images[-1])[best])
    distance = float(np.linalg.norm(GRID[best]) / PIXEL_ARCSEC)
    baseline = [f.baseline(d) for f, d in zip(frames, images)]
    baseline_train = float(np.sqrt(sum(max(0, z) ** 2 for z, _ in baseline[:-1])))
    baseline_holdout = baseline[-1][0]
    return dict(
        fitted_sky_offset_arcsec=GRID[best].tolist(),
        training_nominal_snr=train_snr,
        held_prediction_nominal_snr=holdout_snr,
        predicted_offset_nominal_pixels=distance,
        cross_view_accept=bool(train_snr >= 7 and holdout_snr >= 5 and distance <= 0.5),
        baseline_training_nominal_snr=baseline_train,
        baseline_holdout_nominal_snr=baseline_holdout,
        baseline_centroid_offsets_pixels=[d for _, d in baseline],
        baseline_accept=bool(
            baseline_train >= 7 and baseline_holdout >= 5 and all(d <= 0.5 for _, d in baseline)
        ),
    )


def prepare(tic, sectors):
    source_result = ROOT / "results" / f"{tic}_pixels" / "result.json"
    result = json.loads(source_result.read_text())
    period, epoch, duration = [
        result[key] for key in ["period_days", "epoch_btjd", "duration_days"]
    ]
    out = ROOT / "results/cross_view"
    out.mkdir(exist_ok=True)
    frames, inputs = [], []
    for sector in sectors:
        cache = out / f"{tic}_{sector}.npz"
        if not cache.exists():
            files = list((ROOT / "data/targetpixels" / str(tic)).glob(f"*-s{sector:04d}-*_tp.fits"))
            if len(files) != 1:
                raise ValueError(f"Expected exactly one TPF for {tic}, sector {sector}")
            path = files[0]
            with fits.open(path, memmap=False) as h:
                assert int(h[0].header["TICID"]) == tic
                table = h[1].data
                keep = np.isfinite(table["TIME"]) & (table["QUALITY"] == 0)
                t = np.asarray(table["TIME"][keep], dtype=float)
                cube = np.asarray(table["FLUX"][keep], dtype=float)
                errors = np.asarray(table["FLUX_ERR"][keep], dtype=float)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    wcs = WCS(h[2].header)
                ra, dec = h[0].header["RA_OBJ"], h[0].header["DEC_OBJ"]
                target = np.array(wcs.world_to_pixel_values(ra, dec))
                matrix = wcs.pixel_scale_matrix.copy() * 3600
                matrix[0] *= np.cos(np.radians(dec))
                aperture = (h[2].data.astype(int) & 2) > 0
            actual, nominal, _ = difference_stack(t, cube, errors, period, epoch, duration)
            clear = abs((t - epoch + period / 2) % period - period / 2) > 1.5 * duration
            null = []
            phases = []
            for phase in (np.arange(24) + 0.5) / 24:
                if min(phase, 1 - phase) * period < 4 * duration:
                    continue
                try:
                    image, _, _ = difference_stack(
                        t[clear],
                        cube[clear],
                        errors[clear],
                        period,
                        epoch + phase * period,
                        duration,
                    )
                except ValueError:
                    continue
                null.append(image)
                phases.append(float(phase))
            if len(null) < 12:
                raise ValueError(
                    "Too few off-event images for separate development/evaluation banks"
                )
            null = np.asarray(null)
            # Fit the noise floor on development maps only. Evaluation is not used.
            development = null[::2]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scatter = 1.4826 * np.nanmedian(
                    abs(development - np.nanmedian(development, axis=0)), axis=0
                )
            error = np.maximum(nominal, scatter)
            np.savez_compressed(
                cache,
                actual=actual,
                error=error,
                nominal_error=nominal,
                null=null,
                phases=np.array(phases),
                target=target,
                sky_matrix=matrix,
                aperture=aperture,
                source=str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        data = dict(np.load(cache, allow_pickle=False))
        frames.append(Frame(data))
        inputs.append(
            dict(
                sector=sector,
                source=str(data["source"]),
                sha256=str(data["sha256"]),
                derived_cache_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),
                off_event_maps=len(data["null"]),
            )
        )
    return frames, inputs


def trials(fields, seed, count, evaluation):
    rng = np.random.default_rng(seed)
    rows = []
    labels = ["target", "displaced", "no_injection"]
    for index in range(count):
        tic = list(fields)[index % len(fields)]
        frames = fields[tic]
        label = labels[(index // len(fields)) % 3]
        amplitude_snr = float(rng.uniform(3, 12))
        angle = rng.uniform(0, 2 * np.pi)
        separation = rng.uniform(0.75, 3) if label == "displaced" else 0
        offset = PIXEL_ARCSEC * separation * np.array([np.cos(angle), np.sin(angle)])
        widths = rng.uniform(0.6, 1.0, 2)
        images = []
        for frame in frames:
            bank = frame.data["null"][1::2] if evaluation else frame.data["null"][::2]
            image = bank[rng.integers(len(bank))].copy()
            if label != "no_injection":
                # Inject a shape different from the fixed fitting template.
                xy = frame.xy(offset) + rng.normal(0, 0.05, 2)
                shape = kernel(frame.shape, xy, widths * rng.uniform(0.9, 1.1, 2))
                norm = np.linalg.norm(frame.whiten(shape))
                image += shape * (amplitude_snr * rng.uniform(0.9, 1.1) / norm)
            images.append(image)
        rows.append(
            dict(
                tic=tic,
                label=label,
                trial=index,
                injected_nominal_snr_per_view=amplitude_snr,
                injected_separation_pixels=float(separation),
                **evaluate(frames, images),
            )
        )
    return rows


def summary(rows):
    return {
        label: dict(
            cases=sum(r["label"] == label for r in rows),
            cross_view_accepted=sum(r["cross_view_accept"] for r in rows if r["label"] == label),
            baseline_accepted=sum(r["baseline_accept"] for r in rows if r["label"] == label),
        )
        for label in ["target", "displaced", "no_injection"]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=360)
    args = parser.parse_args()
    if args.cases < 90 or args.cases % 9:
        parser.error("cases must be a multiple of nine and at least 90")
    plan = json.loads((ROOT / "provenance/cross_view_experiment_plan.json").read_text())
    if (
        hashlib.sha256((ROOT / plan["protocol"]).read_bytes()).hexdigest()
        != plan["protocol_sha256"]
    ):
        raise ValueError("Frozen experiment protocol changed")
    fields = {}
    inputs = {}
    real = []
    for tic, sectors in FIELDS.items():
        fields[tic], inputs[tic] = prepare(tic, sectors)
        real.append(dict(tic=tic, **evaluate(fields[tic], [f.data["actual"] for f in fields[tic]])))
        print(json.dumps(real[-1]), flush=True)
    development = trials(fields, plan["development_seed"], args.cases, False)
    evaluation = trials(fields, plan["evaluation_seed"], args.cases, True)
    report = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        protocol_sha256=plan["protocol_sha256"],
        inputs=inputs,
        real_case_studies=real,
        development=summary(development),
        evaluation=summary(evaluation),
        thresholds=dict(training_snr=7, held_prediction_snr=5, maximum_offset_pixels=0.5),
        limitations=[
            "Difference-map injections, not raw-pixel or end-to-end transit recovery.",
            "Gaussian injection and fit families are related; widths differ but both are simplified.",
            "Real off-event maps can contain astrophysical variation and are reused; these are not independent null trials or a global false-alarm estimate.",
            "No held-view position fit; held amplitude is a nominal matched-filter measurement.",
            "Compared with an aperture/centroid diagnostic, not a claim of superiority to all existing pipelines.",
            "Novelty and astrophysical discovery remain unestablished.",
        ],
    )
    out = ROOT / "reports/experiments/cross_view"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, rows in [("development", development), ("evaluation", evaluation)]:
        (out / f"{name}.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["development", "evaluation"]}), flush=True)


if __name__ == "__main__":
    main()
