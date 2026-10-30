"""Write-once ESTIM exact joint engine+opening-fleet scan, no unproven cuts.

The historical C121 functions, GE shortcut, OFF settings/defaults and magic
constant inventory are unchanged. This changes only the opt-in FullScan copy:
evaluate each eligible engine with its already existing N=1/N=2 fused model,
then elect the best engine+fleet pair by decision score, not only by N=1.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

BASE = REPO / 'results/estim31_joint_safe20261030'
DEST = REPO / 'results/estim31_motor_joint20261030'
DESIGNS = ('mix_a200_r150_w05_flat_load25', 'mix_a200_r075_w15_slope',
           'mix_a125_r125_w05_flat_statue0')
FILE = 'ai/OpexAI/air_economics_c121_fullscan.nut'
CHOOSE = 'function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)'
OLD = '''    local economics = (("decisionEconomics" in evaluatedEconomics)
        && evaluatedEconomics.decisionEconomics != null)
        ? evaluatedEconomics.decisionEconomics : evaluatedEconomics;
    evaluated++;
    if (("engineMailKnown" in economics) && economics.engineMailKnown) known++;
    local item = { plane = plane, economics = economics, context = context };
'''
OPENING_OLD = '''    local openingPlanes = 1;
    local evaluatedEconomics = context == null
        ? OpexC121EngineEconomics(catalog, plan, plane, openingPlanes, true, null)
        : OpexC121EngineEconomics(catalog, plan, plane, openingPlanes, true, null, null, context);
'''
OPENING_NEW = '''    /* One fused N=1/N=2 evaluation per engine; never duplicate N=1. */
    local joint = context == null
        ? OpexC121WinnerEconomics(catalog, plan, plane)
        : OpexC121WinnerEconomics(catalog, plan, plane, context);
    local evaluatedEconomics = joint == null ? null : joint.full;
'''
NEW = '''    /* Exact ESTIM economic choice: the N=2 winner can differ by engine.
     * No pruning by upperScore or by airport-level GE cache. Use the
     * existing fused N=1/N=2 function and its exact decision score. */
    if (joint == null || joint.initial == null || joint.full == null) continue;
    local economics = joint.full;
    if (!("decisionScore" in economics)) continue;
    evaluated++;
    if (("engineMailKnown" in economics) && economics.engineMailKnown) known++;
    local item = { plane = plane, economics = economics, context = context,
                   jointEconomics = joint };
'''
WINNER_OLD = '''  local winnerEconomics = best.context == null
      ? OpexC121WinnerEconomics(catalog, plan, best.plane)
      : OpexC121WinnerEconomics(catalog, plan, best.plane, best.context);
'''
WINNER_NEW = '''  /* Already computed for this chosen engine/depth in the exact scan. */
  local winnerEconomics = ("jointEconomics" in best) ? best.jointEconomics
      : (best.context == null ? OpexC121WinnerEconomics(catalog, plan, best.plane)
                              : OpexC121WinnerEconomics(catalog, plan, best.plane, best.context));
'''


def prepare(name):
    if name not in DESIGNS:
        raise ValueError(name)
    base = BASE / name
    dest = DEST / name
    if dest.exists():
        raise FileExistsError(f'Write-once output exists: {dest}')
    for subdir in ('ai','ai_libraries','sweeps'):
        shutil.copytree(base/subdir, dest/subdir)
    for filename in ('Dockerfile','requirements.txt','requirements-ml.txt'):
        shutil.copy2(base/filename, dest/filename)
    file = dest/FILE
    source = file.read_text('utf-8')
    before, sep, chooser = source.partition(CHOOSE)
    if (not sep or chooser.count(OLD) != 1 or chooser.count(WINNER_OLD) != 1
            or chooser.count(OPENING_OLD) != 1):
        raise ValueError('Frozen chooser anchors changed')
    chooser = chooser.replace(OPENING_OLD, OPENING_NEW, 1)
    chooser = chooser.replace(OLD, NEW, 1).replace(WINNER_OLD, WINNER_NEW, 1)
    source = before + sep + chooser
    if source.count('if ((ESTIM_UNIFIE & 1) == 0) {') != 1:
        raise ValueError('ESTIM GE guard missing')
    if 'candidate.upperScore < best.economics.decisionScore' in source:
        raise ValueError('Unsafe prune')
    file.write_text(source,encoding='utf-8')
    design = json.loads((base/'design.json').read_text('utf-8'))
    design.update(engine_objective='exact fused N1/N2 over all physically eligible engines',
                  engine_parent=str(base),
                  joint_scan_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    (dest/'design.json').write_text(json.dumps(design,indent=2)+'\n',encoding='utf-8')
    print('PREPARED_JOINT_MOTOR', name)


if __name__ == '__main__':
    for name in (sys.argv[1:] or DESIGNS):
        prepare(name)
