"""Run a bounded local download/search/refinement tranche with restartable outputs."""
import argparse,json,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--offset',type=int,required=True);p.add_argument('--count',type=int,required=True)
    p.add_argument('--search-workers',type=int,default=2);p.add_argument('--download-workers',type=int,default=3)
    a=p.parse_args();name=f'campaign_{a.offset}_{a.count}';logs=ROOT/'logs';logs.mkdir(exist_ok=True)
    targets=pd.read_csv(ROOT/'data/catalogs/ranked_targets.csv')
    targets=targets[~targets.known_toi_host & ~targets.known_ctoi_host].iloc[a.offset:a.offset+a.count]
    targetfile=ROOT/f'target_batch_{a.offset}_{a.count}.csv';targets.to_csv(targetfile,index=False)
    state={'started_utc':datetime.now(timezone.utc).isoformat(),'offset':a.offset,'count':len(targets),'stage':'starting'}
    def checkpoint(stage):
        state.update(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat())
        (logs/f'{name}.json').write_text(json.dumps(state,indent=2));print(stage,state['updated_utc'],flush=True)
    def command(script,*args):return [sys.executable,str(ROOT/'scripts'/script),*map(str,args)]
    def runstage(stage,cmd):
        checkpoint(stage)
        with (logs/f'{name}_{stage}.log').open('w') as output:
            subprocess.run(cmd,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True)
    try:
        checkpoint('downloading_and_screening')
        with (logs/f'{name}_download.log').open('w') as dl,(logs/f'{name}_search.log').open('w') as sl:
            downloader=subprocess.Popen(command('download.py','--offset',a.offset,'--count',a.count,'--max-sectors',18,'--workers',a.download_workers),cwd=ROOT,stdout=dl,stderr=subprocess.STDOUT)
            searcher=subprocess.Popen(command('batch.py','--target-list',targetfile,'--workers',a.search_workers,'--wait-downloads',14400),cwd=ROOT,stdout=sl,stderr=subprocess.STDOUT)
            try:
                while downloader.poll() is None or searcher.poll() is None:time.sleep(10)
                if downloader.returncode or searcher.returncode:raise RuntimeError(f'download exit={downloader.returncode}; search exit={searcher.returncode}')
            finally:
                for child in [downloader,searcher]:
                    if child.poll() is None:child.terminate()
        runstage('timing_refinement',command('refine.py','--all-screened','--workers',a.search_workers))
        checkpoint('variability_diagnostics')
        with (logs/f'{name}_vetting.log').open('w') as output:
            for tic in targets.TIC.astype(int):
                folder=ROOT/'results'/f'{tic}_refined';result=folder/'result.json'
                if not result.exists():continue
                for s in json.loads(result.read_text()).get('signals',[]):
                    if not s['screening_flags']:
                        subprocess.run(command('vet.py','--tic',tic,'--signal',s['seed_iteration'],'--refined'),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True)
        runstage('exporting',command('summarize.py'))
        checkpoint('finished_pending_human_or_agent_review')
    except Exception as exc:
        state['error']=repr(exc);checkpoint('error');raise

if __name__=='__main__':main()
