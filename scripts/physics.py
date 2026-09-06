"""Explicit approximate stellar irradiation calculations, with source provenance."""
import numpy as np

HZ_SOURCE = 'https://arxiv.org/pdf/2101.07898 (Table 1, equations 1-3)'

def stellar_hz(star):
    # Use the paper's coefficients rather than the CDS EA/RV column labels:
    # the latter are inconsistent with Earth-equivalent luminosity for TOI-700
    # and across this snapshot. Preserve those source columns without relabeling.
    temp=float(star.Teff)-5780.
    inner=np.polynomial.polynomial.polyval(temp,[1.7763,1.4335e-4,3.3954e-9,-7.6364e-12,-1.1950e-15])
    outer=np.polynomial.polynomial.polyval(temp,[.3207,5.4471e-5,1.5275e-9,-2.1709e-12,-3.8282e-16])
    lum=float(star.Rad)**2*(float(star.Teff)/5772.)**4
    period=lambda flux:365.256*np.sqrt((lum/flux)**1.5/float(star.Mass))
    return dict(inner_flux=float(inner),outer_flux=float(outer),
                inner_period=float(period(inner)),outer_period=float(period(outer)),
                earth_period=float(period(1)),luminosity=lum,source=HZ_SOURCE)

def central_duration(period,star,radius_earth=1.):
    """Circular, central transit duration in days; not a measurement."""
    a=(float(star.Mass)*(period/365.256)**2)**(1/3)
    return period/np.pi*np.arcsin(np.clip((float(star.Rad)+radius_earth*.0091577)*.00465047/a,0,1))
