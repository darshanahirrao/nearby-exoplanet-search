"""Bounded local batch screening with restartable, per-target evidence files."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,time
import pandas as pd
from search import analyze,ROOT

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--target-list',required=True)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--tag',default='')
    p.add_argument('--max-signals',type=int,default=4)
    p.add_argument('--wait-downloads',type=int,default=1800,help='maximum seconds waiting for target downloads')
    a=p.parse_args();targets=pd.read_csv(a.target_list).TIC.astype(int).tolist()
    print('BEGIN',datetime.now(timezone.utc).isoformat(),'pid',os.getpid(),'targets',len(targets),flush=True)
    deadline=time.monotonic()+a.wait_downloads
    pending=set(targets);futures={};done=[];skipped=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        while pending or futures:
            for tic in list(pending):
                out=ROOT/'results'/(str(tic)+a.tag)/'result.json'
                if out.exists():
                    old=json.loads(out.read_text())
                    if old.get('status')=='screened':done.append(tic);pending.remove(tic);continue
                s=ROOT/'data/download_status'/f'{tic}.json'
                if not s.exists():continue
                try:status=json.loads(s.read_text())
                except json.JSONDecodeError:continue  # a download may be atomically replaced on next loop
                if status['state']=='downloading':continue
                if len(status.get('files',[]))<2:
                    skipped.append({'tic':tic,'reason':'fewer than two downloaded sectors','download_state':status['state']});pending.remove(tic);continue
                if len(futures)>=a.workers:break
                futures[pool.submit(analyze,tic,a.max_signals,1.5,a.tag)]=tic
                pending.remove(tic)
            completed=[f for f in futures if f.done()]
            for f in completed:
                tic=futures.pop(f)
                try:
                    r=f.result();done.append(tic)
                    signals=r.get('signals',[])
                    print(tic,r['status'],round(r['elapsed_seconds'],1),'signals',len(signals),'unflagged',sum(not s['screening_flags'] for s in signals),r.get('error',''),flush=True)
                except Exception as exc:skipped.append(dict(tic=tic,reason=repr(exc)));print(tic,'worker_error',repr(exc),flush=True)
            if time.monotonic()>deadline and pending and not futures:
                skipped.extend({'tic':tic,'reason':'download unavailable before wait limit'} for tic in pending);pending.clear()
            state={'updated_utc':datetime.now(timezone.utc).isoformat(),'target_list':str(Path(a.target_list).resolve().relative_to(ROOT)),
                   'completed':done,'running':list(futures.values()),'pending':sorted(pending),'skipped':skipped}
            statefile=ROOT/'logs'/f'batch_{Path(a.target_list).stem}{a.tag}.json'
            tmp=statefile.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2));tmp.replace(statefile)
            if pending or futures:time.sleep(3)
    print('END',datetime.now(timezone.utc).isoformat(),'completed',len(done),'skipped',len(skipped),flush=True)

if __name__=='__main__':main()
