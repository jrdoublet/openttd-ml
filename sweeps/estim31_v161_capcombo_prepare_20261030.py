"""Two opt-in V161 × exact C121 motorcap combinations, from the healthy winner.

No new gameplay constants: reuse the already-tested AIR prior value and
existing EB14/statue settings. Write-once; screen 5x5 before any 40x5.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

PARENT = REPO / 'results/estim31_v161_motorcap20261030/mix_a200_r075_w15_slope'
DEST = REPO / 'results/estim31_v161_capcombo20261030'
FILE = 'ai/OpexAI/air_economics_c121_fullscan.nut'
DESIGNS = {
    'v161cap_a250_r075_w15': {'air': 2.5, 'rail': 0.75, 'weight': 15,
                               'eb14': 3, 'v249_statue': 2},
    'v161cap_a200_r075_statue0_eb142': {
        'air': 2.0, 'rail': 0.75, 'weight': 15,
        'eb14': 2, 'v249_statue': 0},
}


def prepare(name):
    if name not in DESIGNS:
        raise ValueError(name)
    new = DEST / name
    if new.exists():
        raise FileExistsError('Write-once output exists: ' + str(new))
    for folder in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(PARENT / folder, new / folder)
    for filename in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(PARENT / filename, new / filename)
    config = DESIGNS[name]
    source = new / FILE
    if config['air'] != 2.0:
        data = source.read_text('utf-8')
        before = 'ESTIM_K_R_PRIOR.air = 2.00;'
        if data.count(before) != 1:
            raise ValueError('Frozen source initial AIR prior is not unique')
        source.write_text(data.replace(before,
                            f"ESTIM_K_R_PRIOR.air = {config['air']:.2f};", 1),
                          encoding='utf-8')
    design = json.loads((PARENT / 'design.json').read_text('utf-8'))
    design['name'] = name
    design['configuration'].update(config)
    design.update(capcombo_parent=str(PARENT),
                  capcombo_interaction='V161 x C121 motorcap x prior/statue/EB14',
                  capcombo_module_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  capcombo_opt_in='ESTIM bit1 only; OFF historical source unchanged')
    design['combined_sha256'][FILE] = design['capcombo_module_sha256']
    (new / 'design.json').write_text(json.dumps(design, indent=2) + '\n', 'utf-8')
    print('PREPARED_CAPCOMBO', name)


if __name__ == '__main__':
    for name in sys.argv[1:] or DESIGNS:
        prepare(name)
