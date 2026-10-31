"""Diagnostic, not qualification: instrument six-month-idle rail repairs over 5y."""
from pathlib import Path
import hashlib, json, sys, os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sweeps'))
import bench_v2, openttdlab
from campaign_freeze import _frozen_library_descriptor
meta=json.loads((ROOT/'results/v233l_frozen_manifest_libraries_20261030.json').read_text(encoding='utf8'))
libdir=ROOT/'results/frozen_rail_libraries_20261030'
groups={g['requested_unique_id']:g['resolved'] for g in meta}
for group in groups.values():
 for item in group:
  if hashlib.sha256((libdir/item['filename']).read_bytes()).hexdigest()!=item['sha256']:
   raise ValueError('Frozen library hash mismatch: '+item['filename'])
def frozen(uid,name):
 return _frozen_library_descriptor(name,groups[uid],libdir)
if os.name == 'nt':
 raise SystemExit('Run this instrumented diagnostic in Docker/Linux so subprocess debug patch inherits via fork')
bench_v2.bananas_ai_library=frozen
check_output=openttdlab.subprocess.check_output
def check_debug(command,*args,**kwargs):
 command=tuple(command)
 if any(str(part).startswith('-vnull') for part in command):
  command=command[:1]+('-d','script=4')+command[1:]
 return check_output(command,*args,**kwargs)
openttdlab.subprocess.check_output=check_debug
# Limit the diagnostic files to relevant motor events; retain script death
# markers and one completed 1974-12 snapshot per world. Economic parsing
# is unchanged, and this instrumented run is not a new adoption gate.
original_keep=bench_v2.keep
WATCH=('RAIL_REPAIR_IDLE','RAIL_SITE_REPAIR','RAIL_ASTAR_REPAIR',
       'RAIL_POSE_REPAIR','V131_REPAIR','RAIL_BUILD',
       'Your script made an error','The script died unexpectedly')
def filtered_keep(row):
 row=dict(row)
 if str(row['date'])=='1974-12-01':
  row['output']='\n'.join(line for line in (row.get('output') or '').splitlines()
                            if any(k in line for k in WATCH))
 else:
  row['output']=''
 return original_keep(row)
bench_v2.keep=filtered_keep
smoke='--smoke' in sys.argv
seeds=[42] if smoke else list(bench_v2.SEEDS_40)
arm='OpexAI[mode_air=0,mode_road=0,mode_water=0,mode_rail=1,rail_repair_join_site=1,rail_repair_v131_focus=1,rail_repair_astar_pair=1,rail_repair_pose_order=1,probes=258]'
name='results/rail_repair_idle_exposure_'+('seed42_light_1x5' if smoke else '40x5')+'_20261030.json'
sys.argv=['bench_v2.py','--arms',arm,'--seeds',*(str(s) for s in seeds),'--years','5','--max-workers','1' if smoke else '8','--out',name]
if __name__=='__main__':bench_v2.main()
