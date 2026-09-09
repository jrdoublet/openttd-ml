"""Diagnostic C41.33 : économie fret rail."""
import argparse,re,sys
from pathlib import Path
import openttdlab
from openttdlab import bananas_ai_library,run_experiments
ROOT=Path('/work') if Path('/work').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sweeps'))
from bench_v2 import OPENGFX_VERSION,OPENTTD_VERSION,arm_statistics,build_arms,enable_savegame_cleanup,experiments,keep,make_cfg,summarise,write_json_atomically
import bench_v2
_old=openttdlab.subprocess.check_output
def debug(a,*x,**k):
 a=tuple(a)
 if any(str(v).startswith('-vnull') for v in a):a=a[:1]+('-d','script=4')+a[1:]
 return _old(a,*x,**k)
openttdlab.subprocess.check_output=debug
ARM='OpexAI[c39_invalidation_probe=1,c41_rail_freight_economics_profile=1]';RE=re.compile(r'OPEX \d+-\d+-\d+ C41_RAIL_FREIGHT_ECONOMICS_PROFILE\s*(.*)')
def main():
 p=argparse.ArgumentParser();p.add_argument('--years',type=int,default=6);p.add_argument('--seeds',nargs='+',type=int,default=[42,100,7,999,12345]);p.add_argument('--max-workers',type=int,default=3);p.add_argument('--out',type=Path,default=None);a=p.parse_args();out=a.out or ROOT/'results'/f'diag_c41_33_rail_freight_economics_{a.years}y_{len(a.seeds)}seeds.json';bench_v2.CHECKPOINT_PATH=out.with_suffix('.jsonl');enable_savegame_cleanup()
 rows=list(run_experiments(openttd_version=OPENTTD_VERSION,opengfx_version=OPENGFX_VERSION,max_workers=a.max_workers,result_processor=keep,experiments=experiments(build_arms([ARM]),a.seeds,a.years,1,1970),ai_libraries=(bananas_ai_library('51554648','Queue.FibonacciHeap'),bananas_ai_library('5046524c','Pathfinder.Rail'))));s=summarise(rows)
 for r in s:
  es=[{k:v for t in z.split() if '=' in t for k,_,v in (t.partition('='),)} for z in RE.findall(r['openttd_output'] or '')];r['c41_freight_economics_ops']=sum(int(e.get('ops',0)) for e in es);r['c41_freight_economics_calls']=sum(int(e.get('calls',0)) for e in es)
 failed=[r for r in s if not r['run_ok']];write_json_atomically(out,{'summary':s,'failed_runs':failed,'statistics':arm_statistics(s,[ARM]),'openttd_config':make_cfg(1970)});print('failed',len(failed),'out',out)
 if failed:raise SystemExit(1)
if __name__=='__main__':main()
