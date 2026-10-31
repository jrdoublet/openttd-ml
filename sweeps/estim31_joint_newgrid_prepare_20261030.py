"""Build an immutable new interaction grid for ESTIM-31 under /results only.

Historical source, settings outside ESTIM and prior defaults remain unchanged;
new values replace existing priors only on the ESTIM-enabled route. No new
production knobs or magic constants are introduced.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

CONFIGS = {
    # name: (prior AIR, prior RAIL, prior weight, flat distance, load25)
    "a200_r075_w15_slope": (2.00, .75, 15., False, False),
    "a175_r100_w30_slope": (1.75, 1.00, 30., False, False),
    "a175_r075_w05_slope": (1.75, .75, 5., False, False),
    "a100_r150_w05_flat": (1.00, 1.50, 5., True, False),
    "a125_r150_w30_flat": (1.25, 1.50, 30., True, False),
    "a175_r125_w30_flat": (1.75, 1.25, 30., True, False),
    "a200_r150_w05_flat_load25": (2.00, 1.50, 5., True, True),
    "a075_r075_w30_slope": (.75, .75, 30., False, False),
    "a125_r075_w05_slope": (1.25, .75, 5., False, False),
    "a100_r150_w15_slope": (1.00, 1.50, 15., False, False),
}

DISPATCH = ('  if ((ESTIM_UNIFIE & 1) != 0)\n'
            '    ::OpexC121ChooseRoutePlane <- OpexC121ChooseRoutePlaneFullScan;')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root, name):
    a, r, w, flat, load25 = CONFIGS[name]
    base = root / 'results/estim31_engine_dispatch_air15_root_20261029'
    target = root / 'results/estim31_joint_newgrid20261030' / name
    if target.exists():
        raise RuntimeError('Refusing to overwrite existing experiment: ' + str(target))
    for folder in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(base / folder, target / folder)
    for file in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(base / file, target / file)
    script = target / 'ai/OpexAI/settings.nut'
    source = script.read_text('utf8')
    if source.count(DISPATCH) != 1:
        raise ValueError('Unexpected ESTIM conditional dispatch in source')
    body = ('  if ((ESTIM_UNIFIE & 1) != 0) {\n'
            '    ::OpexC121ChooseRoutePlane <- OpexC121ChooseRoutePlaneFullScan;\n'
            f'    ESTIM_K_R_PRIOR.air = {a:.2f};\n'
            f'    ESTIM_K_R_PRIOR.rail = {r:.2f};\n'
            f'    ESTIM_K_R_PRIOR_WEIGHT = {w:.1f};\n')
    if flat:
        body += ('    ESTIM_RAIL_KR_PROFILE_A = 0.92;\n'
                 '    ESTIM_RAIL_KR_PROFILE_B = 0.0;\n')
    body += '  }'
    script.write_text(source.replace(DISPATCH, body, 1), 'utf8')
    globals_pre = target / 'ai/OpexAI/globals_pre.nut'
    engine = target / 'ai/OpexAI/air_economics_c121.nut'
    assert globals_pre.read_bytes() == (base / 'ai/OpexAI/globals_pre.nut').read_bytes()
    assert engine.read_bytes() == (base / 'ai/OpexAI/air_economics_c121.nut').read_bytes()
    metadata = {
        'name': name, 'configuration': [a, r, w], 'flat_rail': flat,
        'air_load_min_pct': 25 if load25 else 0,
        'levers': ['optin_prior_after_load'] +
                  (['flat_rail_distance'] if flat else []) +
                  (['air_load_min_pct=25'] if load25 else []),
        'source_root': str(base),
        'source_globals_unchanged': True, 'source_c121_unchanged': True,
        'settings_sha256': digest(script), 'globals_sha256': digest(globals_pre),
        'c121_sha256': digest(engine),
        'active_only_if': '(ESTIM_UNIFIE & 1) != 0',
        'probe_mask': 2, 'eb14_progressive': 3,
        'qualify_40x5_only_after_5x5_screen': True,
    }
    (target / 'design.json').write_text(json.dumps(metadata, indent=2) + '\n', 'utf8')
    print('PREPARED', name, metadata['configuration'], 'flat', flat, 'load25', load25)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('names', nargs='*', choices=tuple(CONFIGS))
    args = parser.parse_args()
    for name in (args.names or CONFIGS):
        prepare(args.repository.resolve(), name)


if __name__ == '__main__':
    main()
