"""Write-once safe ESTIM-31 grid: initialize priors BEFORE every candidate scan.

Historical chooser, settings, and globals are byte-identical to frozen source.
The experimental module cannot bypass the exact scan via C121_GE and never
stops on the unproven engine upper-bound. The old exploratory bundles remain.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys

from sweeps.estim31_joint_next_prepare import BASE, CONFIGS, REPO

# Follow-up crossed interactions from the concurrent 5×5 grid, but with
# corrected load-time initialization and *without* experimental GE bypass.
SAFE_CONFIGS = dict(CONFIGS, **{
    'mix_a200_r150_w05_flat_load25': (2.00, 1.50, 5.0, True, 3, 2, 0, 25),
    'mix_a200_r075_w15_slope': (2.00, 0.75, 15.0, False, 3, 2, 0, 0),
    'mix_a175_r125_w30_flat': (1.75, 1.25, 30.0, True, 3, 2, 0, 0),
})

DEST = REPO / 'results/estim31_joint_safe20261030'
MODULE = 'ai/OpexAI/air_economics_c121_fullscan.nut'
FUNCTION = 'function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)\n{\n'
GATE = '  {\n    local airportType = plan.airport.type;\n    geState = OpexC121GameEngineState(airportType);'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(name):
    if name not in SAFE_CONFIGS:
        raise ValueError(name)
    air, rail, weight, flat, eb14, statue, eb2, load = SAFE_CONFIGS[name]
    target = DEST / name
    if target.exists():
        raise FileExistsError(f'Write-once bundle exists: {target}')
    for directory in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(BASE / directory, target / directory)
    for filename in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(BASE / filename, target / filename)
    fullscan = target / MODULE
    code = fullscan.read_text(encoding='utf-8')
    if code.count(FUNCTION) != 1 or code.count(GATE) != 1:
        raise ValueError('Frozen FullScan anchors changed')
    assignments = (
        '/* ESTIM-only: require() executes in settings AFTER ESTIM is read and BEFORE\n'
        ' * ESTIM_K_R is initialized and any RAIL/AIR candidate scoring begins. */\n'
        f'ESTIM_K_R_PRIOR.air = {air:.2f};\n'
        f'ESTIM_K_R_PRIOR.rail = {rail:.2f};\n'
        f'ESTIM_K_R_PRIOR_WEIGHT = {weight:.1f};\n'
    )
    if flat:
        assignments += ('ESTIM_RAIL_KR_PROFILE_A = 0.92;\n'
                        'ESTIM_RAIL_KR_PROFILE_B = 0.0;\n')
    code = assignments + code
    code = code.replace(GATE,
                        '  /* Historical GE shortcut only runs in the untouched OFF chooser.\n'
                        '   * FullScan must never bypass another engine under ESTIM. */\n'
                        '  if ((ESTIM_UNIFIE & 1) == 0) {\n'
                        '    local airportType = plan.airport.type;\n'
                        '    geState = OpexC121GameEngineState(airportType);', 1)
    if 'if (candidate.upperScore < best.economics.decisionScore)' in code:
        raise ValueError('Unsafe prune appeared')
    fullscan.write_text(code, encoding='utf-8')
    for path in ('settings.nut', 'globals_pre.nut', 'air_economics_c121.nut'):
        rel = Path('ai/OpexAI') / path
        if (target / rel).read_bytes() != (BASE / rel).read_bytes():
            raise ValueError(f'Historical OFF source modified: {path}')
    manifest = dict(name=name, parent_bundle=str(BASE),
                    configuration=dict(air=air, rail=rail, weight=weight,
                        flat_rail=flat, eb14=eb14, v249_statue=statue,
                        eb2_fallback=eb2, air_load_min_pct=load),
                    c121_ge_estimation='disabled; OFF unchanged',
                    prior_initialization='module load before ESTIM_K_R copy',
                    probes=2, opt_in='estim_unifie=31',
                    source_sha256={p:sha(target/'ai/OpexAI'/p) for p in
                        ('air_economics_c121.nut','air_economics_c121_fullscan.nut',
                         'globals_pre.nut','settings.nut')})
    (target/'design.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding='utf-8')
    print('PREPARED', name, manifest['configuration'])


if __name__ == '__main__':
    for name in (sys.argv[1:] or tuple(SAFE_CONFIGS)):
        prepare(name)
