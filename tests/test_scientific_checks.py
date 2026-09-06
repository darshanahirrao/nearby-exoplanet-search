"""Offline sanity checks; real-data validation is separately reported."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from physics import stellar_hz,central_duration
from search import event_checks,split_campaigns

class ScientificChecks(unittest.TestCase):
    def test_earth_units_and_hz_order(self):
        h=stellar_hz(SimpleNamespace(Rad=1,Mass=1,Teff=5772))
        self.assertAlmostEqual(h['earth_period'],365.256,places=4)
        self.assertLess(h['inner_period'],h['earth_period'])
        self.assertGreater(h['outer_period'],h['earth_period'])
        for temp in np.linspace(2600,4500,15):
            h=stellar_hz(SimpleNamespace(Rad=.2,Mass=.2,Teff=temp))
            self.assertGreater(h['inner_flux'],1)
            self.assertTrue(0<h['outer_flux']<1)

    def test_earth_sun_central_duration(self):
        hours=24*central_duration(365.256,SimpleNamespace(Rad=1,Mass=1))
        self.assertTrue(12.9<hours<13.2)

    def test_event_depth_and_empty_holdout(self):
        t=np.arange(0,40,.005)+.00123;phase=(t-1+2.5)%5-2.5
        d=pd.DataFrame(dict(time=t,flux=1-.001*(abs(phase)<.06),err=np.full(len(t),.0002),sector=1))
        r=event_checks(d,5,1,.12)
        self.assertEqual(r['n_observed_events'],8)
        self.assertTrue(all(abs(x['depth']-.001)<1e-10 for x in r['event_snr']))
        self.assertEqual(event_checks(d.iloc[:0],5,1,.12)['n_observed_events'],0)

    def test_campaign_holdout_is_disjoint(self):
        t=np.r_[np.arange(0,20,.02),np.arange(400,410,.02)]
        d,v,_=split_campaigns(pd.DataFrame(dict(time=t,sector=np.where(t<100,1,20))))
        self.assertEqual((len(d),len(v)),(1000,500))
        self.assertFalse(set(d.time)&set(v.time))

if __name__=='__main__':unittest.main()
