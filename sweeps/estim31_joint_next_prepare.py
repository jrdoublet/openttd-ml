"""Write-once ESTIM-31 interaction bundles (no production/default changes).

Copy the already audited historical C121/main and fullscan-on-demand module.
All experiment-specific coefficients are assigned only inside the ESTIM module
and therefore can never execute on the OFF path. No new production constants.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BASE = REPO / 'results/estim31_joint_dispatch20261029/module_a150_r100_w15'
DEST = REPO / 'results/estim31_joint_next20261030'

# Every row alters at least two independently meaningful controls.
# Coefficients and profile constants already exist in historic trials.
CONFIGS = {
    'mix_a100_w15_statue0_eb2': (1.00, 1.00, 15.0, False, 3, 0, 1, 0),
    'mix_a100_w15_statue0_load25': (1.00, 1.00, 15.0, False, 3, 0, 0, 25),
    'mix_a125_r125_w05_flat_statue0': (1.25, 1.25, 5.0, True, 3, 0, 0, 0),
    'mix_a125_w15_eb142_load25': (1.25, 1.00, 15.0, False, 2, 2, 0, 25),
    'mix_a100_r125_w15_eb142_statue0': (1.00, 1.25, 15.0, False, 2, 0, 0, 0),
    'mix_a125_w15_eb2_load25': (1.25, 1.00, 15.0, False, 3, 2, 1, 25),
    'mix_a150_w15_statue0_eb2': (1.50, 1.00, 15.0, False, 3, 0, 1, 0),
    'mix_a075_r125_w15_statue0': (0.75, 1.25, 15.0, False, 3, 0, 0, 0),
}

ANCHOR = 'function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)\n{\n'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(name):
    if name not in CONFIGS:
        raise ValueError(name)
    params = CONFIGS[name]
    air, rail, weight, flat, eb14, statue, eb2, load = params
    target = DEST / name
    if target.exists():
        raise FileExistsError(f'Write-once experiment already exists: {target}')
    if not (BASE/'design.json').is_file():
        raise FileNotFoundError('Frozen provenance source absent')
    for folder in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(BASE/folder, target/folder)
    for file in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(BASE/file, target/file)
    historical = target/'ai/OpexAI/air_economics_c121.nut'
    globals_file = target/'ai/OpexAI/globals_pre.nut'
    assert historical.read_bytes() == (BASE/'ai/OpexAI/air_economics_c121.nut').read_bytes()
    assert globals_file.read_bytes() == (BASE/'ai/OpexAI/globals_pre.nut').read_bytes()
    module = target/'ai/OpexAI/air_economics_c121_fullscan.nut'
    code = module.read_text(encoding='utf8')
    assert code.count(ANCHOR) == 1
    condition=(f'ESTIM_K_R_PRIOR.air != {air:.2f} || '
               f'ESTIM_K_R_PRIOR.rail != {rail:.2f} || '
               f'ESTIM_K_R_PRIOR_WEIGHT != {weight:.1f}')
    if flat:
        condition += ' || ESTIM_RAIL_KR_PROFILE_B != 0.0'
    updates = (
        '  /* ESTIM-only one-time interaction controls; OFF never requires this file. */\n'
        f'  if ({condition}) {{\n'
        f'  ESTIM_K_R_PRIOR.air = {air:.2f};\n'
        f'  ESTIM_K_R_PRIOR.rail = {rail:.2f};\n'
        f'  ESTIM_K_R_PRIOR_WEIGHT = {weight:.1f};\n'
        f'  ESTIM_K_R.air = {air:.2f};\n'
        f'  ESTIM_K_R.rail = {rail:.2f};\n'
    )
    if flat:
        updates += ('  ESTIM_RAIL_KR_PROFILE_A = 0.92;\n'
                    '  ESTIM_RAIL_KR_PROFILE_B = 0.0;\n')
    updates+='  }\n'
    module.write_text(code.replace(ANCHOR, ANCHOR+updates, 1), encoding='utf8')
    # Important: the real historical C121 and globals remain unchanged,
    # and settings.nut dispatch itself is also byte-identical to BASE.
    settings = target/'ai/OpexAI/settings.nut'
    assert settings.read_bytes() == (BASE/'ai/OpexAI/settings.nut').read_bytes()
    manifest = dict(name=name, configuration=dict(air=air, rail=rail, weight=weight,
                   flat_rail=flat, eb14=eb14, v249_statue=statue, eb2_fallback=eb2,
                   air_load_min_pct=load),
                   prior_source_bundle=str(BASE), optin='estim_unifie=31',
                   source_sha256={p:digest(target/'ai/OpexAI'/p) for p in (
                       'air_economics_c121.nut','air_economics_c121_fullscan.nut',
                       'globals_pre.nut','settings.nut')}, probes=2)
    (target/'design.json').write_text(json.dumps(manifest,indent=2)+'\n','utf8')
    print('PREPARED',name,manifest['configuration'])


if __name__ == '__main__':
    targets = sys.argv[1:] or list(CONFIGS)
    for target in targets: prepare(target)
