# Periodic subtraction from a spatially protected reference

Static spatial cancellation failed its development gate. This experiment instead
estimates the neighbor's repeating pattern by averaging over time. It uses the
catalogue position of TIC 608579111 (RA 0.440267096131202, Dec 69.5015238397358
degrees), which is consistent with the two approximate difference-image positions.
This is a positional association, not a unique source classification or discovery.

For nominal target and neighbor footprints `p` and `n`, construct minimum-noise
reference weights `q` satisfying `q.T p = 0` and `q.T n = 1`. The reference rejects
the nominal target footprint. Set the subtraction coefficient `c = b.T n`, where
`b` is the fixed aperture normalized to the nominal target. Estimate the repeating
component with `L = Q Q.T`: `Q` is an orthonormal basis for three harmonics of the
previously fixed 0.37769418149605544-day period, after removing a constant and
linear trend. The output is `X b - lambda c L X q`.

Everything defining this linear operator comes from times, nominal pixel errors,
fixed catalogue positions and fixed models, not the measured output flux. The
operator is saved before evaluating it. If target and neighbor cannot be separated
numerically, use the aperture with zero subtraction strength.

For an injected spatial footprint `p_i` and temporal transit vector `u`, the
fractional matched-template depth response, after removing the same time trend,
is exactly `1 - lambda c (q.T p_i)/(b.T p_i) f(u)`, where
`f(u) = ||Q.T u||^2 / ||u - T T.T u||^2` and `T` is the trend basis. Choose
`lambda <= 1` from the worst response over a finite certificate family so its
modeled depth loss is at most 1%. This is a finite-model certificate, not a claim
about every actual transit or point-spread function.

The spatial certificate uses the same 81 Gaussian target footprints as earlier
pixel experiments. The temporal family includes 24 logarithmically spaced
periods from 3 to 40 days, all integer multiples of the nuisance period within
that interval, eight phases, durations 0.025/0.05/0.10/0.15 days, and both box and
trapezoid shapes. Test 300 fresh random spatial/temporal combinations per sector,
including periods commensurate with the nuisance, after freezing the operator.

Compare aperture extraction, direct subtraction of the same temporal basis from
the aperture, and the protected-reference output. Propagate the exact diagonal
pixel-noise covariance through the linear operator, including shared-pixel
covariance. Off-diagonal temporal covariance is present and is not converted into
a calibrated search false-alarm probability by these checks.

Use sectors 17 and 58 for development. Proceed unchanged to sectors 18/24/25/52
only if development has median two-hour scatter at most 0.90 of the aperture,
no sector above 1.05 of aperture two-hour or rapid scatter, median periodic RMS
at most 0.50 of the aperture, no more than 5% median two-hour scatter penalty
relative to direct temporal subtraction, and at least 0.99 template-depth response
in every unseen injection draw. The same gate applies to the four additional
pixel views. They were not used for pixel-extraction development, but their scalar
light curves were inspected previously. Passing only warrants full raw-injection
period-recovery tests. No planet or methodological novelty is established.
