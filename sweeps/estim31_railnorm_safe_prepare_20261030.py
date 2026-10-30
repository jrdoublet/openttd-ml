"""Write-once interaction: safe early priors + exhaustive engines + RAIL norm.

Normalize the gross RAIL learning denominator for the existing distance shape,
conditional on ESTIM bit16. Compare to the exact unnormalized safe source.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

BASE = REPO / 'results/estim31_joint_safe20261030'
DEST = REPO / 'results/estim31_railnorm_safe20261030'
DESIGNS = ('mix_a125_r125_w05_flat_statue0',
           'mix_a100_r125_w15_eb142_statue0')
ANCHOR = '''  local pred = mode == "air" ? line.c121RawRevenueAnnual
      : (("predRevenue" in line) ? line.predRevenue : 0);
'''
PATCH = '''  /* ESTIM bit16: learn a RAIL level, not the distance shape applied at
   * selection; predRevenue stored on line is the unscaled raw gross value. */
  if (mode == "rail" && (ESTIM_UNIFIE & 16) != 0
      && ("distance" in line) && line.distance > 0 && ESTIM_K_R.rail > 0.0)
    pred = pred.tofloat() * OpexEstimRailRevenueFactor(line.distance) / ESTIM_K_R.rail;
'''


def prepare(name):
    if name not in DESIGNS:
        raise ValueError(name)
    src, dst = BASE / name, DEST / name
    if dst.exists():
        raise FileExistsError(f'Frozen output exists: {dst}')
    for directory in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(src / directory, dst / directory)
    for f in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(src / f, dst / f)
    filename = 'ai/OpexAI/projects_models.nut'
    path = dst / filename
    code = path.read_text('utf-8')
    if code.count(ANCHOR) != 1:
        raise ValueError('RAIL learning anchor missing')
    path.write_text(code.replace(ANCHOR, ANCHOR+PATCH, 1), encoding='utf-8')
    parent = json.loads((src/'design.json').read_text('utf-8'))
    parent.update(railnorm='distance-shape normalization ESTIM bit16',
                  railnorm_parent=str(src),
                  norm_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (dst/'design.json').write_text(json.dumps(parent,indent=2)+'\n',encoding='utf-8')
    print('PREPARED railnorm_safe', name)


if __name__ == '__main__':
    for name in (sys.argv[1:] or DESIGNS):
        prepare(name)
