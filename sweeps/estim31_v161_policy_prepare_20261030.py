"""Frozen V161 factorial: isolate statues, EB14 scheduling, and AIR load.

All variants share byte-identical historical OFF and opt-in source with the
already tested AIR2/RAIL0.75 V161 bundle. Only runtime settings change;
there are zero added product-side constants or hard-coded decision thresholds.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

ROOT = REPO / 'results'
PARENT = ROOT / 'estim31_v161_safe20261030/mix_a200_r075_w15_slope'
DEST = ROOT / 'estim31_v161_policy20261030'
MIX = {
    'v161_a200_r075_w15_statue0': dict(v249_statue=0),
    'v161_a200_r075_w15_eb142': dict(eb14=2),
    'v161_a200_r075_w15_load25': dict(air_load_min_pct=25),
    'v161_a200_r075_w15_statue0_eb142': dict(v249_statue=0, eb14=2),
}


def file_map(folder):
    return {str(path.relative_to(folder)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (folder / 'ai').rglob('*') if path.is_file()}


def prepare(name):
    if name not in MIX:
        raise ValueError(name)
    target = DEST / name
    if target.exists():
        raise FileExistsError(f'Write-once result exists: {target}')
    for subdir in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(PARENT / subdir, target / subdir)
    for file in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(PARENT / file, target / file)
    if file_map(PARENT) != file_map(target):
        raise ValueError('Unexpected source change')
    design = json.loads((PARENT / 'design.json').read_text('utf-8'))
    design['name'] = name
    design['configuration'].update(MIX[name])
    design.update(v161_policy_parent=str(PARENT),
                  v161_policy_factors=MIX[name],
                  immutable_ai_source_hashes=file_map(target))
    (target / 'design.json').write_text(json.dumps(design, indent=2) + '\n', 'utf-8')
    print('PREPARED_V161_POLICY', name)


if __name__ == '__main__':
    for item in (sys.argv[1:] or MIX):
        prepare(item)
