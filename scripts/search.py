"""Exploratory transit screening. Outputs are signals, NOT validated planets.

Fits independently detrended observing campaigns and a held-back campaign.
All S/N values are nominal screening statistics, not calibrated false-alarm rates.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, time, traceback, warnings
import hashlib
import numpy as np
import pandas as pd
from scipy.ndimage import median_filter
from astropy.io import fits
from astropy.timeseries import BoxLeastSquares
from physics import stellar_hz, central_duration

ROOT=Path(__file__).resolve().parents[1]
RESULT=ROOT/'results'
RESULT.mkdir(exist_ok=True)

def robust_sigma(x):
    x=np.asarray(x);x=x[np.isfinite(x)]
    if len(x)<3:return np.nan
    return 1.4826*np.median(np.abs(x-np.median(x)))

def bin_series(t,y,e,step=10/1440):
    ix=np.floor((t-t[0])/step).astype(int)
    w=1/np.maximum(e,1e-8)**2
    sw=np.bincount(ix,weights=w);valid=sw>0
    return (np.bincount(ix,weights=t*w)[valid]/sw[valid],
            np.bincount(ix,weights=y*w)[valid]/sw[valid],1/np.sqrt(sw[valid]))

def load_target(tic, flux_column='PDCSAP_FLUX', window_days=1.5, inject=None):
    arrays=[]; metadata=[]
    for path in sorted((ROOT/'data/lightcurves'/str(tic)).glob('*_lc.fits')):
        with fits.open(path,memmap=False) as h:
            d=h[1].data;header=h[0].header
            t=np.array(d['TIME'],dtype=float);y=np.array(d[flux_column],dtype=float)
            e=np.array(d[flux_column+'_ERR'],dtype=float);q=np.array(d['QUALITY'])
            good=np.isfinite(t)&np.isfinite(y)&np.isfinite(e)&(e>0)&(y>0)&(q==0)
            t,y,e=t[good],y[good],e[good]
            if len(t)<100:continue
            order=np.argsort(t);t,y,e=t[order],y[order],e[order]
            if inject is not None:
                phase=(t-inject['epoch']+.5*inject['period'])%inject['period']-.5*inject['period']
                y=y*(1-inject['depth']*(np.abs(phase)<inject['duration']/2))
            median=np.median(y);y=y/median;e=e/median
            sector=int(header.get('SECTOR',h[1].header.get('SECTOR',-1)))
            # Treat gaps independently to avoid fitting across spacecraft interruptions.
            splits=np.r_[0,np.where(np.diff(t)>.3)[0]+1,len(t)]
            for left,right in zip(splits[:-1],splits[1:]):
                tt,yy,ee=t[left:right],y[left:right],e[left:right]
                if len(tt)<80 or np.ptp(tt)<.8:continue
                tt,yy,ee=bin_series(tt,yy,ee)
                if len(tt)<30:continue
                cadence=np.median(np.diff(tt));window=max(9,int(window_days/cadence)//2*2+1)
                window=min(window,len(tt)//2*2-1)
                trend=median_filter(yy,size=window,mode='nearest')
                flat=yy/trend;err=ee/trend
                # Remove large upward flares, while retaining all downward transit-like events.
                sigma=max(robust_sigma(np.diff(flat))/np.sqrt(2),float(np.median(err)),1e-6)
                keep=(tt>tt[0]+.10)&(tt<tt[-1]-.10)&(flat<1+6*sigma)
                err=np.maximum(err,sigma)
                arrays.append(pd.DataFrame({'time':tt[keep],'flux':flat[keep],'err':err[keep],
                                            'raw_flux':yy[keep],'trend':trend[keep],'sector':sector}))
            metadata.append({'file':str(path.relative_to(ROOT)),'sector':sector,'good_raw_points':len(t),
                             'crowdsap':float(h[1].header.get('CROWDSAP',np.nan)),
                             'flfrcsap':float(h[1].header.get('FLFRCSAP',np.nan))})
    if not arrays:raise ValueError('no usable light curves')
    df=pd.concat(arrays).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    return df,metadata

def split_campaigns(df):
    df=df.copy();df['campaign']=np.r_[0,np.cumsum(np.diff(df.time)>100)]
    sizes=df.groupby('campaign').size()
    best=int(sizes.idxmax())
    if len(sizes)>1:
        discovery=df[df.campaign==best].copy();validation=df[df.campaign!=best].copy()
        method='largest observing campaign vs separate campaigns (>100 day gap)'
    else:
        sectors=np.sort(df.sector.unique())
        if len(sectors)>=4:
            discovery=df[df.sector.isin(sectors[::2])].copy()
            validation=df[df.sector.isin(sectors[1::2])].copy()
            method='alternating sectors within one campaign'
        else:
            discovery=df.copy();validation=df.iloc[0:0].copy();method='no independent sector holdout available'
    return discovery,validation,method

def scan(df,low,high,star,max_signals=4):
    t=df.time.to_numpy();y=df.flux.to_numpy();e=df.err.to_numpy()
    baseline=np.ptp(t);low=max(1.0,float(low));high=min(float(high),baseline*.48,100)
    if high<=low or len(t)<300:return [],{}
    # A logarithmic grid bounds transit phase drift by about 1/4 of the shortest searched duration.
    durations=np.array([.025,.04,.06,.09,.13,.18,.25])
    durations=durations[durations<low*.12]
    nperiods=int(np.ceil(np.log(high/low)*4*baseline/durations.min()))+1
    nperiods=max(3000,nperiods)
    periods=np.geomspace(low,high,nperiods)
    remaining=np.ones(len(t),dtype=bool);signals=[]
    for iteration in range(max_signals):
        if remaining.sum()<300:break
        model=BoxLeastSquares(t[remaining],y[remaining],e[remaining])
        power=model.power(periods,durations,objective='likelihood',method='fast',oversample=5)
        k=int(np.nanargmax(power.power));period=float(power.period[k]);duration=float(power.duration[k]);epoch=float(power.transit_time[k])
        depth=float(power.depth[k]);snr=float(power.depth_snr[k])
        # Refine locally using only discovery data; freeze before examining held-back observations.
        dp=periods[min(k+1,len(periods)-1)]-periods[max(0,k-1)]
        fine=np.linspace(max(low,period-2*dp),min(high,period+2*dp),401)
        ref=model.power(fine,np.unique(np.clip(duration*np.array([.75,1,1.25]),durations.min(),durations.max())),objective='likelihood',oversample=10)
        j=int(np.nanargmax(ref.power));period=float(ref.period[j]);duration=float(ref.duration[j]);epoch=float(ref.transit_time[j]);depth=float(ref.depth[j]);snr=float(ref.depth_snr[j])
        mad=robust_sigma(power.power);sde=float((power.power[k]-np.median(power.power))/max(mad,1e-9))
        sig={'period_days':period,'epoch_btjd':epoch,'duration_days':duration,'depth':depth,'nominal_bls_snr':snr,'periodogram_robust_z':sde,'iteration':iteration+1}
        # Event diagnostics must use the same masked observations as this iteration.
        sig.update(event_checks(df.iloc[np.flatnonzero(remaining)],period,epoch,duration))
        sig['radius_earth_estimate']=float(np.sqrt(max(depth,0))*float(star.Rad)/.0091577)
        a=(float(star.Mass)*(period/365.256)**2)**(1/3)
        lum=float(star.Rad)**2*(float(star.Teff)/5772)**4
        sig['irradiation_earth_estimate']=lum/a**2
        hz=stellar_hz(star)
        sig['in_optimistic_hz']=bool(hz['inner_period']<=period<=hz['outer_period'])
        sig['central_circular_duration_days']=float(central_duration(period,star,sig['radius_earth_estimate']))
        signals.append(sig)
        if snr<5:break
        phase=(t-epoch+period/2)%period-period/2
        remaining&=np.abs(phase)>duration*1.25
    return signals,{'minimum_period':low,'maximum_period':high,'n_periods':nperiods,'durations_days':durations.tolist(),'baseline_days':float(baseline)}

def event_checks(df,period,epoch,duration):
    if len(df)==0:return {'n_observed_events':0,'n_positive_events':0,'event_snr':[],'fixed_ephemeris_snr':None}
    t=df.time.to_numpy();y=df.flux.to_numpy();e=df.err.to_numpy()
    phase=(t-epoch+period/2)%period-period/2
    transit=np.abs(phase)<duration/2
    cycles=np.rint((t-epoch)/period).astype(int)
    records=[]
    for cycle in np.unique(cycles[transit]):
        center=epoch+cycle*period
        inside=(np.abs(t-center)<duration/2)
        outside=(np.abs(t-center)>duration)&(np.abs(t-center)<max(4*duration,.3))
        if inside.sum()<3 or outside.sum()<8:continue
        w=1/e[inside]**2;wo=1/e[outside]**2
        dep=float(np.sum(wo*y[outside])/sum(wo)-np.sum(w*y[inside])/sum(w))
        error=float(np.sqrt(1/sum(w)+1/sum(wo)))
        records.append({'cycle':int(cycle),'center_btjd':float(center),'points':int(inside.sum()),'depth':dep,'error':error,'snr':dep/error})
    if records:
        dep=np.array([x['depth'] for x in records]);err=np.array([x['error'] for x in records]);w=1/err**2
        total=float(np.sum(w*dep)/np.sqrt(sum(w)))
        positive=int(sum(dep>0));sum_sq=sum(max(x['snr'],0)**2 for x in records)
        dominance=max(max(x['snr'],0)**2 for x in records)/max(sum_sq,1e-20)
        # Event-to-event odd/even discrepancy is a screening diagnostic, not an EB verdict.
        sides=[]
        for parity in [0,1]:
            sel=np.array([x['cycle']%2==parity for x in records])
            if sel.any():sides.append((float(sum(w[sel]*dep[sel])/sum(w[sel])),float(1/np.sqrt(sum(w[sel])))))
        odd_even=abs(sides[0][0]-sides[1][0])/np.hypot(sides[0][1],sides[1][1]) if len(sides)==2 else None
    else:total=0.;positive=0;dominance=None;odd_even=None
    return {'n_observed_events':len(records),'n_positive_events':positive,'event_snr':records,
            'fixed_ephemeris_snr':total,'single_event_power_fraction':dominance,'odd_even_sigma':odd_even}

def known_matches(tic,period):
    found=[]
    for fname,idcol,namecol,pcol in [('exofop_toi.csv','TIC ID','TOI','Period (days)'),('exofop_ctoi.csv','TIC ID','CTOI','Period (days)')]:
        p=ROOT/'data/catalogs'/fname
        if not p.exists():continue
        data=pd.read_csv(p);data=data[pd.to_numeric(data[idcol],errors='coerce')==tic]
        for _,row in data.iterrows():
            kp=pd.to_numeric(row[pcol],errors='coerce')
            if np.isfinite(kp) and kp>0:
                for ratio in [.5,1,2,3,1/3]:
                    if abs(period/(kp*ratio)-1)<.01:found.append({'catalogue':fname,'id':str(row[namecol]),'period':float(kp),'period_ratio':ratio})
    p=ROOT/'data/catalogs/confirmed_planets.csv'
    if p.exists():
        data=pd.read_csv(p);ids=pd.to_numeric(data.tic_id.astype(str).str.replace('TIC ','',regex=False),errors='coerce')
        for _,row in data[ids==tic].iterrows():
            kp=row.pl_orbper
            if np.isfinite(kp) and kp>0:
                for ratio in [.5,1,2,3,1/3]:
                    if abs(period/(kp*ratio)-1)<.01:found.append({'catalogue':'confirmed_planets.csv','id':row.pl_name,'period':float(kp),'period_ratio':ratio})
    return found

def mask_known_inner(df,tic,minimum_period):
    """Remove already catalogued short-period TOI transits; document every mask."""
    data=pd.read_csv(ROOT/'data/catalogs/exofop_toi.csv')
    data=data[pd.to_numeric(data['TIC ID'],errors='coerce')==tic]
    keep=np.ones(len(df),dtype=bool);masks=[]
    for _,row in data.iterrows():
        p=pd.to_numeric(row['Period (days)'],errors='coerce')
        epoch=pd.to_numeric(row['Epoch (BJD)'],errors='coerce')-2457000
        dur=pd.to_numeric(row['Duration (hours)'],errors='coerce')/24
        if np.isfinite([p,epoch,dur]).all() and 0<p<minimum_period and dur>0:
            phase=(df.time.to_numpy()-epoch+p/2)%p-p/2
            keep&=np.abs(phase)>dur*1.5
            masks.append(dict(toi=str(row['TOI']),period_days=float(p),epoch_btjd=float(epoch),half_width_days=float(dur*1.5)))
    return df.iloc[np.flatnonzero(keep)].copy(),masks

def analyze(tic,max_signals=4,window_days=1.5,output_tag=''):
    start=time.monotonic();outdir=RESULT/(str(tic)+output_tag);outdir.mkdir(exist_ok=True)
    result={'tic':int(tic),'started_utc':datetime.now(timezone.utc).isoformat(),'status':'running','claims':'Exploratory signals only. No confirmed discovery.'}
    try:
        stars=pd.read_csv(ROOT/'data/catalogs/all_hz_targets.csv');star=stars[stars.TIC==int(tic)].iloc[0]
        df,meta=load_target(tic,window_days=window_days)
        hz=stellar_hz(star)
        df,masks=mask_known_inner(df,int(tic),max(1,.85*hz['inner_period']))
        discovery,validation,split=split_campaigns(df)
        result.update(star=star.to_dict(),files=meta,points=len(df),discovery_points=len(discovery),validation_points=len(validation),split_method=split,
                      discovery_sectors=sorted(map(int,discovery.sector.unique())),validation_sectors=sorted(map(int,validation.sector.unique())),detrend_window_days=window_days,
                      hz_physics=hz,known_inner_transit_masks=masks,
                      search_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        df.to_csv(outdir/'lightcurve.csv.gz',index=False)
        sig,config=scan(discovery,max(1,.85*hz['inner_period']),min(100,1.15*hz['outer_period']),star,max_signals)
        # This file records the discovery results before any held-back data are inspected.
        (outdir/'frozen_discovery.json').write_text(json.dumps({'signals':sig,'config':config,'frozen_utc':datetime.now(timezone.utc).isoformat()},indent=2,default=float))
        for s in sig:
            s['validation']=event_checks(validation,s['period_days'],s['epoch_btjd'],s['duration_days'])
            s['known_matches']=known_matches(int(tic),s['period_days'])
            flags=[]
            if s['known_matches']:flags.append('known_catalogue_signal_or_harmonic')
            if s['n_observed_events']<3:flags.append('fewer_than_three_discovery_events')
            if s.get('single_event_power_fraction') is not None and s['single_event_power_fraction']>.6:flags.append('dominated_by_one_event')
            if s.get('odd_even_sigma') is not None and s['odd_even_sigma']>3:flags.append('odd_even_discrepancy')
            if not s['in_optimistic_hz']:flags.append('outside_nominal_optimistic_hz')
            if s['duration_days']>1.6*s['central_circular_duration_days']:flags.append('long_relative_to_circular_transit')
            if not .5<=s['radius_earth_estimate']<=2:flags.append('outside_initial_small_planet_radius_range')
            if len(validation)==0:flags.append('no_independent_holdout')
            elif s['validation']['n_observed_events']<2:flags.append('insufficient_holdout_events')
            elif (s['validation']['fixed_ephemeris_snr'] or 0)<5:flags.append('not_recovered_at_fixed_ephemeris')
            if s['nominal_bls_snr']<7:flags.append('low_nominal_snr')
            s['screening_flags']=flags
            s['screening_status']='requires_detailed_vetting' if not flags else 'flagged_screening_signal'
        result.update(status='screened',search_config=config,signals=sig)
    except Exception as e:result.update(status='error',error=repr(e),traceback=traceback.format_exc())
    result['elapsed_seconds']=time.monotonic()-start
    (outdir/'result.json').write_text(json.dumps(result,indent=2,default=float))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--tics',nargs='*',type=int);p.add_argument('--all-downloaded',action='store_true');p.add_argument('--max-signals',type=int,default=4);p.add_argument('--window',type=float,default=1.5);p.add_argument('--tag',default='')
    a=p.parse_args()
    tics=a.tics or []
    if a.all_downloaded:
        for p in sorted((ROOT/'data/download_status').glob('*.json')):
            s=json.loads(p.read_text())
            if s['state']=='downloaded' and len(s['files'])>=3 and not (RESULT/(str(s['tic'])+a.tag)/'result.json').exists():tics.append(s['tic'])
    for tic in tics:
        r=analyze(tic,a.max_signals,a.window,a.tag)
        print(tic,r['status'],round(r['elapsed_seconds'],2),[(round(s['period_days'],5),round(s['nominal_bls_snr'],1),s['screening_flags']) for s in r.get('signals',[])],r.get('error',''),flush=True)

if __name__=='__main__':main()
