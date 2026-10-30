"""Write-once cross of exact C121 fleet-cap engine selection and V161 margin.

The two opt-in experiments have the same immutable safe parent. Prove that
their source differences are disjoint before merging, preserving the original
OFF chooser and every public default. No new product tuning constants.
"""
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import REPO

ROOT = REPO / 'results'
BASE = ROOT / 'estim31_joint_safe20261030'
MOTOR = ROOT / 'estim31_motor_cap20261030'
MARGIN = ROOT / 'estim31_v161_safe20261030'
DEST = ROOT / 'estim31_v161_motorcap20261030'
NAMES = ('mix_a200_r075_w15_slope', 'mix_a200_r150_w05_flat_load25')
MOTOR_FILE = 'ai/OpexAI/air_economics_c121_fullscan.nut'
MARGIN_FILES = tuple('ai/OpexAI/' + name for name in
                     ('air_fleet.nut', 'task_air.nut', 'task_projects.nut'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_files(parent, child):
    first = {p.relative_to(parent).as_posix(): digest(p)
             for p in (parent / 'ai').rglob('*') if p.is_file()}
    second = {p.relative_to(child).as_posix(): digest(p)
              for p in (child / 'ai').rglob('*') if p.is_file()}
    if first.keys() != second.keys():
        raise ValueError('Bundle AI file set changed')
    return {key for key in first if first[key] != second[key]}


def prepare(name):
    if name not in NAMES:
        raise ValueError(name)
    base, motor, margin, dest = (directory / name
                                for directory in (BASE, MOTOR, MARGIN, DEST))
    if dest.exists():
        raise FileExistsError(f'Write-once output already exists: {dest}')
    if changed_files(base, motor) != {MOTOR_FILE}:
        raise ValueError('Motor variant has unexpected source changes')
    if changed_files(base, margin) != set(MARGIN_FILES):
        raise ValueError('V161 variant has unexpected source changes')
    base_config = json.loads((base / 'design.json').read_text('utf-8'))['configuration']
    for source in (motor, margin):
        if json.loads((source / 'design.json').read_text('utf-8'))['configuration'] != base_config:
            raise ValueError('Different economic parameter tuple')
    for folder in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(motor / folder, dest / folder)
    for filename in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(motor / filename, dest / filename)
    for filename in MARGIN_FILES:
        shutil.copy2(margin / filename, dest / filename)
    design = json.loads((motor / 'design.json').read_text('utf-8'))
    design.update(interaction='C121 exact N1/N2 fleet bound x V161 same-engine marginal',
                  v161_same_engine='Only ESTIM bit1, source files copied from validated V161',
                  parents={'safe': str(base), 'motorcap': str(motor),
                           'v161': str(margin)},
                  combined_sha256={f: digest(dest / f)
                                   for f in (MOTOR_FILE, *MARGIN_FILES)})
    (dest / 'design.json').write_text(json.dumps(design, indent=2) + '\n',
                                      encoding='utf-8')
    print('PREPARED_V161_MOTORCAP', name)


if __name__ == '__main__':
    for selected in (sys.argv[1:] or NAMES):
        prepare(selected)
