"""Four additional V161 AIR×RAIL learned-prior interactions, opt-in only.

Change only existing early-initialization ESTIM prior assignments in a
frozen experimental C121 FullScan source. No defaults, historical OFF, other
business formulas or number of numeric constants in the product are changed.
Write-once output; not qualified without 5x5 plus healthy paired 40x5.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

ROOT = REPO / 'results'
PARENT = ROOT / 'estim31_v161_safe20261030/mix_a200_r075_w15_slope'
DEST = ROOT / 'estim31_v161_coeff20261030'
FILE = 'ai/OpexAI/air_economics_c121_fullscan.nut'
DESIGNS = {
    'v161_a200_r050_w15': (2.0, 0.5, 15),
    'v161_a225_r075_w15': (2.25, 0.75, 15),
    'v161_a225_r050_w05': (2.25, 0.5, 5),
    'v161_a250_r075_w15': (2.5, 0.75, 15),
}


def prepare(name):
    if name not in DESIGNS:
        raise ValueError(name)
    a, r, w = DESIGNS[name]
    dest = DEST / name
    if dest.exists():
        raise FileExistsError(f'Write-once output exists: {dest}')
    for subdir in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(PARENT / subdir, dest / subdir)
    for filename in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(PARENT / filename, dest / filename)
    fullscan = dest / FILE
    text = fullscan.read_text('utf-8')
    for before, after in (
        ('ESTIM_K_R_PRIOR.air = 2.00;', f'ESTIM_K_R_PRIOR.air = {a:.2f};'),
        ('ESTIM_K_R_PRIOR.rail = 0.75;', f'ESTIM_K_R_PRIOR.rail = {r:.2f};'),
        ('ESTIM_K_R_PRIOR_WEIGHT = 15.0;', f'ESTIM_K_R_PRIOR_WEIGHT = {w:.1f};'),
    ):
        if text.count(before) != 1:
            raise ValueError(f'Frozen prior source unexpectedly changed: {before}')
        text = text.replace(before, after, 1)
    fullscan.write_text(text, encoding='utf-8')
    design = json.loads((PARENT / 'design.json').read_text('utf-8'))
    design['name'] = name
    design['configuration'].update(air=a, rail=r, weight=w)
    design.update(prior_optimization='early ESTIM load only, default OFF intact',
                  frozen_parent=str(PARENT),
                  prior_module_sha256=hashlib.sha256(fullscan.read_bytes()).hexdigest())
    (dest / 'design.json').write_text(json.dumps(design, indent=2) + '\n', 'utf-8')
    print('PREPARED_V161_COEFF', name)


if __name__ == '__main__':
    for selected in (sys.argv[1:] or DESIGNS):
        prepare(selected)
