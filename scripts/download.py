"""Cache public SPOC light curves; a few concurrent targets, no bulk sky download."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse, hashlib, json, time, traceback, warnings
import pandas as pd
from astropy.table import Table
import lightkurve as lk
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
for p in ['products','lightcurves','download_status']:(DATA/p).mkdir(exist_ok=True,parents=True)

def download_target(tic, max_sectors=18):
    tic=int(tic); start=time.monotonic(); status={'tic':tic,'files':[],'errors':[]}
    dest=DATA/'download_status'/f'{tic}.json'
    try:
        cache=DATA/'products'/f'{tic}.ecsv'
        if cache.exists():table=Table.read(cache)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result=lk.search_lightcurve(f'TIC {tic}',mission='TESS',author='SPOC',exptime=120)
            table=result.table;table.write(cache,overwrite=True)
        status['available_products']=len(table)
        if len(table)==0:
            status['state']='no_120s_spoc';dest.write_text(json.dumps(status,indent=2));return status
        if 'sequence_number' in table.colnames:table.sort('sequence_number')
        # Preserve a substantial early campaign and an independent late campaign.
        if max_sectors and len(table)>max_sectors:
            count=max_sectors//2
            table=table[list(range(count))+list(range(len(table)-(max_sectors-count),len(table)))]
        (DATA/'lightcurves'/str(tic)).mkdir(exist_ok=True)
        session=requests.Session()
        for row in table:
            filename=str(row['productFilename']);uri=str(row['dataURI'])
            p=DATA/'lightcurves'/str(tic)/filename
            url='https://mast.stsci.edu/api/v0.1/Download/file?'+requests.compat.urlencode({'uri':uri})
            if not p.exists():
                for attempt in range(3):
                    try:
                        r=session.get(url,timeout=(15,100));r.raise_for_status()
                        if not r.content.startswith(b'SIMPLE'):raise ValueError('response is not a FITS primary HDU')
                        tmp=p.with_suffix('.part');tmp.write_bytes(r.content);tmp.replace(p);break
                    except Exception as e:
                        if attempt==2:status['errors'].append({'file':filename,'error':repr(e)})
                        else:time.sleep(2*(attempt+1))
            if p.exists():status['files'].append({'path':str(p.relative_to(ROOT)),'uri':uri,'url':url,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            status['state']='downloading';status['updated_utc']=datetime.now(timezone.utc).isoformat()
            dest.write_text(json.dumps(status,indent=2))
        status['state']='downloaded' if not status['errors'] else 'partial_download'
    except Exception as e:status.update(state='error',error=repr(e),traceback=traceback.format_exc())
    status['elapsed_seconds']=round(time.monotonic()-start,2)
    status['updated_utc']=datetime.now(timezone.utc).isoformat();dest.write_text(json.dumps(status,indent=2))
    return status

def main():
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=60);p.add_argument('--offset',type=int,default=0)
    p.add_argument('--tics',nargs='*',type=int);p.add_argument('--max-sectors',type=int,default=18);p.add_argument('--workers',type=int,default=3)
    a=p.parse_args()
    if a.tics:tics=a.tics
    else:
        t=pd.read_csv(DATA/'catalogs/ranked_targets.csv')
        t=t[~t.known_toi_host & ~t.known_ctoi_host]
        t=t.iloc[a.offset:a.offset+a.count];t.to_csv(ROOT/f'target_batch_{a.offset}_{a.count}.csv',index=False)
        tics=t.TIC.astype(int).tolist()
    print('BEGIN',datetime.now(timezone.utc).isoformat(),'targets',len(tics),'max_sectors',a.max_sectors,flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs=[pool.submit(download_target,tic,a.max_sectors) for tic in tics]
        for i,j in enumerate(as_completed(jobs),1):
            s=j.result();print(i,len(tics),s['tic'],s['state'],len(s['files']),s.get('elapsed_seconds'),s.get('error',''),flush=True)
    print('END',datetime.now(timezone.utc).isoformat(),flush=True)

if __name__=='__main__':main()
