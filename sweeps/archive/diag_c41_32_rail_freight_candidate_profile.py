"""Diagnostic C41.32 : candidats fret rail, 5×6 par défaut."""
import argparse,json,re,sys
from pathlib import Path
import openttdlab
from openttdlab import bananas_ai_library,run_experiments
ROOT=Path('/work') if Path('/work').exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sweeps'))
from bench_v2 import OPENGFX_VERSION,OPENTTD_VERSION,arm_statistics,build_arms,enable_savegame_cleanup,experiments,keep,make_cfg,summarise,write_json_atomically
import bench_v2
_check=openttdlab.subprocess.check_output
def debug(args,*rest,**kwargs):
 args=tuple(args)
 if any(str(a).startswith('-vnull') for a in args): args=args[:1]+('-d','script=4')+args[1:]
 return _check(args,*rest,**kwargs)
openttdlab.subprocess.check_output=debug
ARM='OpexAI[c39_invalidation_probe=1,c41_rail_freight_candidate_profile=1]'
RE=re.compile(r'(OPEX (\d+-\d+-\d+) C41_RAIL_FREIGHT_CANDIDATE_PROFILE\s*(.*))')
def parse(o):
 seen=set();out=[]
 for raw,date,fields in RE.findall(o or ''):
  if raw in seen: continue
  seen.add(raw);out.append({'date':date,**{k:v for t in fields.split() if '=' in t for k,_,v in (t.partition('='),)}})
 return out
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--years',type=int,default=6);p.add_argument('--seeds',nargs='+',type=int,default=[42,100,7,999,12345]);p.add_argument('--max-workers',type=int,default=3);p.add_argument('--out',type=Path,default=None);a=p.parse_args()
 if a.years<=0 or not a.seeds or a.max_workers not in (1,2,3):p.error('arguments invalides')
 out=a.out or ROOT/'results'/f'diag_c41_32_rail_freight_candidate_profile_{a.years}y_{len(a.seeds)}seeds.json';bench_v2.CHECKPOINT_PATH=out.with_suffix('.jsonl')
 if bench_v2.CHECKPOINT_PATH.exists():bench_v2.CHECKPOINT_PATH.unlink()
 enable_savegame_cleanup();rows=list(run_experiments(openttd_version=OPENTTD_VERSION,opengfx_version=OPENGFX_VERSION,max_workers=a.max_workers,result_processor=keep,experiments=experiments(build_arms([ARM]),a.seeds,a.years,1,1970),ai_libraries=(bananas_ai_library('51554648','Queue.FibonacciHeap'),bananas_ai_library('5046524c','Pathfinder.Rail'))));summary=summarise(rows)
 for r in summary:
  es=parse(r['openttd_output']);r['c41_rail_freight_candidate_profiles']=es
  for k in ('industry_ops','industry_candidate_ops','industry_candidate_calls','town_ops','town_candidate_ops','town_candidate_calls'):r['c41_freight_'+k]=sum(int(e.get(k,0)) for e in es)
 failed=[r for r in summary if not r['run_ok']];write_json_atomically(out,{'years':a.years,'seeds':a.seeds,'arms':[ARM],'openttd_config':make_cfg(1970),'summary':summary,'failed_runs':failed,'statistics':arm_statistics(summary,[ARM])});print('failed',len(failed),'out',out)
 if failed:raise SystemExit(1)
if __name__=='__main__':main()
