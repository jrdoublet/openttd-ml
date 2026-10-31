"""Audit historical C121 exact identity and ESTIM-only motor full scan.

This is a source contract, not a substitute for an in-game seed999 check.
The baseline is read from immutable Git history, never from dirty master.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


HISTORICAL = ('OpexC121ChooseRoutePlane', 'OpexC121ScanRoutePlaneEngines')


def source_function(text, name):
    pattern = r'(?ms)^function\s+' + re.escape(name) + r'\([^\n]*\).*?^\}'
    matches = re.findall(pattern, text)
    if len(matches) != 1:
        raise ValueError('Missing or duplicate C121 function ' + name)
    return matches[0]


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def validate(source, historical):
    base = source / 'air_economics_c121.nut'
    full = source / 'air_economics_c121_fullscan.nut'
    settings = source / 'settings.nut'
    if not all(p.is_file() for p in (base, full, settings)):
        raise ValueError('Missing C121 production source files')
    code = base.read_text('utf-8')
    opt = full.read_text('utf-8')
    cfg = settings.read_text('utf-8')
    preserved = {}
    for name in HISTORICAL:
        old, new = source_function(historical, name), source_function(code, name)
        if old != new:
            raise ValueError('Historical C121 function altered: ' + name)
        preserved[name] = digest(old)
    if not re.search(r'if\s*\(\(ESTIM_UNIFIE\s*&\s*1\)\s*!=\s*0\)\s*\{\s*'
                     r'require\("air_economics_c121_fullscan.nut"\);\s*'
                     r'::OpexC121ChooseRoutePlane\s*<-\s*OpexC121ChooseRoutePlaneFullScan;',
                     cfg):
        raise ValueError('FullScan is not dispatched exclusively under ESTIM bit1')
    if 'if ((ESTIM_UNIFIE & 1) == 0) {' not in opt:
        raise ValueError('Missing ESTIM guard around historical GE shortcut')
    if '/* ESTIM: unsafe bound cannot truncate this scan. */' not in opt:
        raise ValueError('No explicit ESTIM non-pruning assurance')
    if re.search(r'if\s*\(\s*upperScore\s*<\s*best', opt):
        raise ValueError('Unsafe economic upperScore pruning under ESTIM')
    if not all('function ' + name + '(' in opt for name in (
            'OpexC121ScanRoutePlaneEnginesFullScan',
            'OpexC121ChooseRoutePlaneFullScan')):
        raise ValueError('Incomplete full-scan functions')
    if 'joint.full.planes > joint.full.fleetScanCap' not in opt:
        # This bound applies specifically to the N1/N2 motorcap variant;
        # other qualified variants use their own validated N1 logic.
        fleet_bound = 'N1 physical only'
    else:
        fleet_bound = 'N1/N2 exact physical cap'
    return {
        'historical_functions_byte_identical_to_git': preserved,
        'ESTIM_bit1_only_dispatch': True,
        'historical_GE_disabled_under_ESTIM': True,
        'no_unproven_economic_upperScore_pruning': True,
        'fleet_bound': fleet_bound,
        'limitations': 'Static source audit only; does not count physical engine purchases',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--git-worktree', type=Path, required=True)
    ap.add_argument('--baseline-commit', default='99f29d9c')
    ap.add_argument('--installed-ai', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    historical = subprocess.check_output([
        'git', '-C', str(args.git_worktree), 'show',
        args.baseline_commit + ':ai/OpexAI/air_economics_c121.nut',
    ]).decode('utf-8')
    data = validate(args.installed_ai.resolve(), historical)
    data['baseline_commit'] = args.baseline_commit
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('HISTORICAL_C121_AND_ESTIM_FULLSCAN_OK', data['fleet_bound'])


if __name__ == '__main__':
    main()
