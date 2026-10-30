"""Isolate ESTIM31 RAIL learned-level distance composition correction.

No new fixed coefficient: the existing OpexEstimRailRevenueFactor(distance)
supplies the profile; divide out its current learned scalar to normalize the
predicted baseline before learning the next scalar. OFF never visits this
path (annual estimRevSums is disabled when ESTIM_UNIFIE == 0).
"""
from pathlib import Path
import json
import shutil
import hashlib

WORKTREE=Path(__file__).resolve().parents[1]
REPO=WORKTREE.parents[1]
BASE=REPO/'results/estim31_joint_dispatch20261029/module_a150_r100_w15'
DEST=REPO/'results/estim31_railnorm20261030'
CONFIGS={
  'railnorm_a125_r125_w15_slope_statue0':(1.25,1.25,15.0,3,0,0),
  'railnorm_a125_r125_w15_slope_eb142_load25':(1.25,1.25,15.0,2,2,25),
}
ANCHOR='function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)\n{\n'
OLD=('  local pred = mode == "air" ? line.c121RawRevenueAnnual\n'
     '      : (("predRevenue" in line) ? line.predRevenue : 0);\n')
NEW=(OLD+
     '  /* ESTIM bit16: calibrate the learned RAIL level after removing the\n'
     '   * distance shape already applied to candidate scores. OFF unchanged. */\n'
     '  if (mode == "rail" && (ESTIM_UNIFIE & 16) != 0\n'
     '      && ("distance" in line) && line.distance > 0 && ESTIM_K_R.rail > 0.0)\n'
     '    pred = pred.tofloat() * OpexEstimRailRevenueFactor(line.distance) / ESTIM_K_R.rail;\n')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(name):
    a,r,w,eb,statue,load=CONFIGS[name]
    dest=DEST/name
    if dest.exists():raise FileExistsError(dest)
    for item in ('ai','ai_libraries','sweeps'):
        shutil.copytree(BASE/item,dest/item)
    for item in ('Dockerfile','requirements.txt','requirements-ml.txt'):
        shutil.copy2(BASE/item,dest/item)
    model=dest/'ai/OpexAI/projects_models.nut'
    text=model.read_text('utf8')
    assert text.count(OLD)==1
    model.write_text(text.replace(OLD,NEW,1),'utf8')
    fullscan=dest/'ai/OpexAI/air_economics_c121_fullscan.nut'
    script=fullscan.read_text('utf8')
    assert script.count(ANCHOR)==1
    code=(f'  if (ESTIM_K_R_PRIOR.air != {a:.2f} || ESTIM_K_R_PRIOR.rail != {r:.2f}\n'
          f'      || ESTIM_K_R_PRIOR_WEIGHT != {w:.1f}) {{\n'
          f'    ESTIM_K_R_PRIOR.air = {a:.2f};\n'
          f'    ESTIM_K_R_PRIOR.rail = {r:.2f};\n'
          f'    ESTIM_K_R_PRIOR_WEIGHT = {w:.1f};\n'
          f'    ESTIM_K_R.air = {a:.2f};\n'
          f'    ESTIM_K_R.rail = {r:.2f};\n'
          '  }\n')
    fullscan.write_text(script.replace(ANCHOR,ANCHOR+code,1),'utf8')
    for file in ('settings.nut','globals_pre.nut','air_economics_c121.nut'):
        assert (BASE/'ai/OpexAI'/file).read_bytes()==(dest/'ai/OpexAI'/file).read_bytes()
    info={'name':name,'configuration':{'air':a,'rail':r,'prior_weight':w,
       'eb14_progressive':eb,'v249_statue':statue,'air_load_min_pct':load},
       'rail_learning':'normalize_predicted_revenue_by_existing_distance_profile',
       'optin_guard':'(ESTIM_UNIFIE & 16) != 0','historical_c121_sha256':sha(dest/'ai/OpexAI/air_economics_c121.nut'),
       'projects_models_sha256':sha(model),'fullscan_sha256':sha(fullscan),'probes':2}
    (dest/'design.json').write_text(json.dumps(info,indent=2)+'\n','utf8')
    print('PREPARED',name)

if __name__=='__main__':
    for k in CONFIGS:prepare(k)
