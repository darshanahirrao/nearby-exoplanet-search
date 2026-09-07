"""Limb-darkened, exposure-integrated injections before our LC processing.

Models use batman (Kreidberg 2015). These are synthetic signals added to public
SPOC PDCSAP data; upstream SPOC processing losses are not reproduced.
"""

import inspect

import setuptools  # noqa: F401 -- register vendored distutils for batman's Python 3.12 import
import batman
import numpy as np

import search

BOX_LINE = 'y = y * (1 - inject["depth"] * (np.abs(phase) < inject["duration"] / 2))'


def model_flux(t, case, star, exposure_days=120 / 86400):
    if case["radius_earth"] == 0:
        return np.ones(len(t))
    params = batman.TransitParams()
    params.t0 = float(case["epoch_btjd"])
    params.per = float(case["period_days"])
    params.rp = float(case["radius_earth"] * 0.0091577 / star.Rad)
    params.a = float((star.Mass * (params.per / 365.256) ** 2) ** (1 / 3) / (star.Rad * 0.00465047))
    params.inc = float(np.rad2deg(np.arccos(case["impact_parameter"] / params.a)))
    params.ecc = 0.0
    params.w = 90.0
    params.u = case.get("limb_darkening", [0.3, 0.2])
    params.limb_dark = "quadratic"
    model = batman.TransitModel(
        params,
        np.ascontiguousarray(t, dtype=float),
        supersample_factor=7,
        exp_time=exposure_days,
        nthreads=1,
    )
    return model.light_curve(params)


def total_duration(case, star):
    period = case["period_days"]
    k = case["radius_earth"] * 0.0091577 / star.Rad
    b = case["impact_parameter"]
    a_rs = (star.Mass * (period / 365.256) ** 2) ** (1 / 3) / (star.Rad * 0.00465047)
    return float(
        period / np.pi * np.arcsin(np.sqrt(((1 + k) ** 2 - b * b) / (a_rs * a_rs - b * b)))
    )


def make_loader(case, star):
    # Reuse our exact frozen loader; replace only the raw injection shape. The
    # phase calculation preceding this line is harmless and remains unchanged.
    source = inspect.getsource(search.load_target)
    if source.count(BOX_LINE) != 1:
        raise ValueError("Raw injection location changed; review the adapter")
    namespace = dict(vars(search), realistic_case=case, realistic_star=star, model_flux=model_flux)
    source = source.replace(BOX_LINE, "y = y * model_flux(t, realistic_case, realistic_star)")
    exec(compile(source, "<realistic-raw-injection>", "exec"), namespace)
    return namespace["load_target"]
