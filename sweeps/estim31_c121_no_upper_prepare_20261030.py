"""Prereg experimental C121 scan: enumerate physically valid planes directly.

No economic upper-score bound, candidate sorting or hidden null reject. This
experiment ONLY changes the ESTIM-loaded FullScan; the two historical C121
functions, GE shortcut, OFF source, settings and numeric constants are intact.
It tests whether removing the now-useless bound calculation saves opcodes and
allows more AIR/RAIL investments within the game's timing budget.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

ROOT = REPO / 'results'
DEST = ROOT / 'estim31_no_upper20261030'
FILE = 'ai/OpexAI/air_economics_c121_fullscan.nut'
DESIGNS = {
    'v161_a200_r075': 'estim31_v161_safe20261030/mix_a200_r075_w15_slope',
    'v161_motorcap_a200_r075': 'estim31_v161_motorcap20261030/mix_a200_r075_w15_slope',
}
OLD = '''  local candidates = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    local context = null;
    local upperScore = context == null ? OpexC121InitialEngineUpperScore(catalog, plan, plane)
        : OpexC121InitialEngineUpperScore(catalog, plan, plane, context);
    if (upperScore == null) continue;
    if (context != null) {
      context.upperScore = upperScore;
      candidates.append(context);
    } else candidates.append({ plane = plane, upperScore = upperScore });
  }
  candidates.sort(function(a, b) {
    if (a.upperScore > b.upperScore) return -1;
    if (a.upperScore < b.upperScore) return 1;
    if (a.plane.id < b.plane.id) return -1;
    if (a.plane.id > b.plane.id) return 1;
    return 0;
  });
'''
NEW = '''  /* ESTIM: exhaustive scan of all physically admissible plane choices,
   * without even evaluating the non-proven C121 initial upper score.
   * Stable catalog order is sufficient: final ties compare engine id. */
  local candidates = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    candidates.append({ plane = plane });
  }
'''


def prepare(name):
    if name not in DESIGNS:
        raise ValueError(name)
    src, dst = ROOT / DESIGNS[name], DEST / name
    if dst.exists():
        raise FileExistsError(f'Write-once output exists: {dst}')
    for directory in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(src / directory, dst / directory)
    for filename in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(src / filename, dst / filename)
    code = (dst / FILE).read_text('utf-8')
    if code.count(OLD) != 2:
        raise ValueError(f'Expected exactly 2 ESTIM scan blocks, found {code.count(OLD)}')
    code = code.replace(OLD, NEW)
    if ('local upperScore' in code or 'a.upperScore' in code
            or 'OpexC121InitialEngineUpperScore(' in code
            or code.count('candidates.append({ plane = plane });') != 2):
        raise ValueError('An unsafe upper score remains in the ESTIM scan')
    (dst / FILE).write_text(code, encoding='utf-8')
    design = json.loads((src / 'design.json').read_text('utf-8'))
    design.update(name=name, no_upper_bound=True,
                  source_parent=str(src),
                  no_upper_scan_sha256=hashlib.sha256((dst / FILE).read_bytes()).hexdigest())
    (dst / 'design.json').write_text(json.dumps(design, indent=2) + '\n', encoding='utf-8')
    print('PREPARED_NO_UPPER', name)


if __name__ == '__main__':
    for name in (sys.argv[1:] or DESIGNS):
        prepare(name)
