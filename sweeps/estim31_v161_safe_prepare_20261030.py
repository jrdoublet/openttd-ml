"""Experimental same-engine marginal fleet growth, default ESTIM=0 untouched.

Couples learned AIR/RAIL priors and exact V161 net marginal yield with V252:
allow profitable growth in the live engine even if V252 would choose an
upgrade using its older solo-line criterion; force that same engine at buy.
No new magic numeric constants, no public setting or default changed.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

ROOT=REPO/'results'
DEST=ROOT/'estim31_v161_safe20261030'
DESIGNS={
 'mix_a200_r150_w05_flat_load25':'estim31_joint_safe20261030',
 'mix_a200_r075_w15_slope':'estim31_joint_safe20261030',
 'mix_a125_r125_w05_flat_statue0':'estim31_motor_joint20261030',
}


def replace_one(text,old,new,name):
    if text.count(old)!=1:
        raise ValueError(f'Anchor {name} changed: {text.count(old)}')
    return text.replace(old,new,1)


def prepare(name):
    src=ROOT/DESIGNS[name]/name
    dst=DEST/name
    if dst.exists():
        raise FileExistsError(f'No overwrite: {dst}')
    for folder in ('ai','ai_libraries','sweeps'):
        shutil.copytree(src/folder,dst/folder)
    for filename in ('Dockerfile','requirements.txt','requirements-ml.txt'):
        shutil.copy2(src/filename,dst/filename)
    af=dst/'ai/OpexAI/air_fleet.nut'
    code=af.read_text('utf-8')
    code=replace_one(code,
        'function OpexAirAddPlane(line, catalog = null, lines = null)',
        'function OpexAirAddPlane(line, catalog = null, lines = null, forcedEngine = null)',
        'signature')
    code=replace_one(code,
        '''  local oldEngine = AIVehicle.GetEngineType(template);
  local targetEngine = oldEngine;

  if (catalog != null) {''',
        '''  local oldEngine = AIVehicle.GetEngineType(template);
  local targetEngine = oldEngine;
  /* The marginal model prices a SAME-engine acquisition. Never mix a
   * V252 suggested replacement into a verified V161 marginal purchase. */
  if (forcedEngine != null && (forcedEngine != oldEngine
      || !AIEngine.IsValidEngine(forcedEngine) || !AIEngine.IsBuildable(forcedEngine))) {
    result.reason = "MARGINAL_ENGINE_STALE"; return result;
  }

  if (catalog != null && forcedEngine == null) {''',
        'force engine guard')
    code=replace_one(code,
        '''  local upgrade = OpexAirBestEngineForLine(line, catalog);
  if (upgrade != null && upgrade != engineId) return null;''',
        '''  /* Under this isolated ESTIM experiment, a profitable same-engine
   * marginal growth can be priced without the unrelated V252 upgrade veto.
   * Outside ESTIM the historical veto remains exactly as before. */
  if ((ESTIM_UNIFIE & 1) == 0) {
    local upgrade = OpexAirBestEngineForLine(line, catalog);
    if (upgrade != null && upgrade != engineId) return null;
  }''',
        'upgrade veto')
    af.write_text(code,encoding='utf-8')
    pj=dst/'ai/OpexAI/task_projects.nut'
    code=pj.read_text('utf-8')
    code=replace_one(code,
        '''    local grown = OpexAirAddPlane(line, this._catalog, this._lines);''',
        '''    /* The revalidated V161 quote explicitly names its live engine. */
    local locked = ((ESTIM_UNIFIE & 1) != 0 && ("v161Engine" in entry))
        ? entry.v161Engine : null;
    local grown = OpexAirAddPlane(line, this._catalog, this._lines, locked);''',
        'project purchase')
    pj.write_text(code,encoding='utf-8')
    ta=dst/'ai/OpexAI/task_air.nut'
    code=ta.read_text('utf-8')
    code=replace_one(code,
        '''      local grown = OpexAirAddPlane(line, this._catalog, this._lines);''',
        '''      local locked = ((ESTIM_UNIFIE & 1) != 0) ? nextMargin.engine : null;
      local grown = OpexAirAddPlane(line, this._catalog, this._lines, locked);''',
        'direct purchase')
    ta.write_text(code,encoding='utf-8')
    design=json.loads((src/'design.json').read_text('utf-8'))
    design.update(v161_marginal_same_engine='forced only under ESTIM bit1',
                  v161_parent=str(src),
                  v161_changed_shas={fn:hashlib.sha256((dst/'ai/OpexAI'/fn).read_bytes()).hexdigest()
                     for fn in ('air_fleet.nut','task_air.nut','task_projects.nut')})
    (dst/'design.json').write_text(json.dumps(design,indent=2)+'\n',encoding='utf-8')
    print('PREPARED_V161_SAME_ENGINE',name)


if __name__=='__main__':
    for name in (sys.argv[1:] or tuple(DESIGNS)):
        prepare(name)
