"""Opt-in first-year rail funding exposure, isolated from immutable V161 parent.

EB3's early rail catalogue already exists, but first-year funding removes
every rail alternative. Test the economic consequence of allowing funded rail
to compete while ESTIM is enabled (no additional constants). Preserve OFF
bit-identical execution and all other source files. Write-once bundle.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

from sweeps.estim31_joint_next_prepare import REPO

ROOT = REPO / 'results'
BASE = ROOT / 'estim31_v161_safe20261030/mix_a200_r075_w15_slope'
DEST = ROOT / 'estim31_v161_rail1970_20261030'
NAME = 'v161_a200_r075_allow_rail1970'
FILE = 'ai/OpexAI/projects.nut'
OLD = 'if (EB3_RAIL_FIRST_YEAR_PREFETCH && MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE) {'
NEW = ('if (EB3_RAIL_FIRST_YEAR_PREFETCH && MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE'
       ' && ((ESTIM_UNIFIE & 1) == 0)) {')


def hashes(folder):
    return {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (folder / 'ai').rglob('*') if p.is_file()
    }


def prepare(name=NAME):
    if name != NAME:
        raise ValueError(f'Unknown experiment: {name}')
    dest = DEST / name
    if dest.exists():
        raise FileExistsError(f'Existing output, write-once: {dest}')
    for sub in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(BASE / sub, dest / sub)
    for file in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(BASE / file, dest / file)
    target = dest / FILE
    src = target.read_text('utf-8')
    if src.count(OLD) != 1:
        raise ValueError(f'Wrong frozen first-year exclusion count: {src.count(OLD)}')
    target.write_text(src.replace(OLD, NEW, 1), encoding='utf-8')
    before, after = hashes(BASE), hashes(dest)
    if set(before) != set(after) or {k for k in before if before[k] != after[k]} != {FILE}:
        raise ValueError('Unexpected source modifications')
    design = json.loads((BASE / 'design.json').read_text('utf-8'))
    design.update(name=name, first_year_rail_finance='ESTIM-only remove EB3 exclusion of all rail',
                  original_source=str(BASE), source_modified_files=[FILE],
                  modified_source_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (dest / 'design.json').write_text(json.dumps(design, indent=2) + '\n', 'utf-8')
    print('PREPARED_RAIL1970', name)


if __name__ == '__main__':
    for name in (sys.argv[1:] or [NAME]):
        prepare(name)
