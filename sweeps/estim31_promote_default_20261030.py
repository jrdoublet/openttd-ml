"""Promote a fully verified top-three 20x10 winner into an isolated Git worktree.

This never edits shared master or the frozen benchmark. It mirrors the exact
tested OpexAI files (rather than attempting to reimplement their complex
interactions) and changes only existing settings' default values. Dry-run
by default; --apply requires that ALL three 20x10 games were qualified and
one distinct winner is present. Keep old values as selectable overrides.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from sweeps.estim31_top3_20x10_20261030 import SUITES_ALL, analyze


def edit_setting(code, name, value):
    pat = re.compile(r'AddSetting\(\{\s*name\s*=\s*"' + re.escape(name)
                     + r'"\s*,.*?\}\);', re.S)
    matches = list(pat.finditer(code))
    if len(matches) != 1:
        raise ValueError('Setting missing or duplicate: ' + name)
    block = matches[0].group()
    keys = ('easy_value', 'medium_value', 'hard_value', 'custom_value')
    if name != 'probes':
        keys += ('default_value',)
    for key in keys:
        sub = re.compile(r'(\b' + re.escape(key) + r'\s*=\s*)\d+')
        if len(sub.findall(block)) != 1:
            raise ValueError('Setting ' + name + ' missing unique ' + key)
        block = sub.sub(lambda m: m.group(1) + str(value), block, count=1)
    if name == 'estim_unifie':
        block = block.replace('0 = historical (default)',
                              '0 = historical (opt-out); 31 = qualified default')
    elif name == 'eb14_progressive':
        block = block.replace('0=off (default)', '0=off (opt-out); 3=qualified default')
    elif name == 'probes':
        if 'default_value' in block:
            raise ValueError('Unexpected explicit probes default in source')
        block = block.replace('0 none (default)',
                              '0 none (opt-out); 2 signs = qualified default')
    return code[:matches[0].start()] + block + code[matches[0].end():]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def promote(repo, worktree, result, apply=False):
    if apply:
        branch = subprocess.check_output(
            ['git', '-C', str(worktree), 'branch', '--show-current'],
            text=True).strip()
        if branch in ('main', 'master') or not branch:
            raise ValueError('Never apply to shared master/main or detached HEAD')
        dirty = subprocess.check_output(
            ['git', '-C', str(worktree), 'status', '--porcelain',
             '--untracked-files=all'], text=True).strip()
        if dirty:
            raise ValueError('Promotion target contains concurrent/unstaged modifications')
    finalists = result.get('ranked_healthy_20x10', [])
    winner = result.get('winner')
    if (len(finalists) != 3 or not winner
            or winner['health'] != '40/40 complete'
            or any(row['health'] != '40/40 complete' for row in finalists)
            or winner != max(finalists, key=lambda row: row['ratio_pct'])):
        raise ValueError('No fully qualified unique top-three 20x10 winner')
    if sorted((r['ratio_pct'] for r in finalists), reverse=True)[0] <= sorted(
            (r['ratio_pct'] for r in finalists), reverse=True)[1]:
        raise ValueError('Tie at best ten-year economic ratio; no unique winner')
    frozen_path = worktree / 'docs/estim31_top3_frozen_20261030.json'
    if not frozen_path.is_file():
        raise ValueError('Missing frozen 40x5 top-three evidence')
    frozen = json.loads(frozen_path.read_text('utf-8'))
    rechecked = analyze(repo, frozen)
    if (rechecked['winner'] != winner or
            rechecked['ranked_healthy_20x10'] != finalists or
            rechecked['not_yet_qualified']):
        raise ValueError('Fresh 20x10 game/manifest revalidation failed')
    folder, _ = SUITES_ALL[winner['suite']]
    bundle = repo / 'results' / folder / winner['name']
    source = bundle / 'ai/OpexAI'
    target = worktree / 'ai/OpexAI'
    if not (source / 'info.nut').is_file() or not target.is_dir():
        raise ValueError('Missing tested OpexAI bundle or destination')
    src = {p.relative_to(source): p for p in source.rglob('*') if p.is_file()}
    dst = {p.relative_to(target): p for p in target.rglob('*') if p.is_file()}
    if dst.keys() - src.keys():
        raise ValueError('Unmapped production-only files: ' +
                         ', '.join(str(k) for k in sorted(dst.keys() - src.keys())))
    design = json.loads((bundle / 'design.json').read_text('utf-8'))
    cfg = design['configuration']
    defaults = {'estim_unifie': 31, 'eb14_progressive': cfg['eb14'],
                'probes': 2}
    for key, setting, old_default in (
            ('v249_statue', 'v249_statue', 2),
            ('eb2_fallback', 'eb2_new_station_fallback', 0),
            ('air_load_min_pct', 'air_load_min_pct', 0)):
        if cfg[key] != old_default:
            defaults[setting] = cfg[key]
    info = (source / 'info.nut').read_text('utf-8')
    for setting, value in defaults.items():
        info = edit_setting(info, setting, value)
    changed = []
    for rel, file in sorted(src.items()):
        new_bytes = info.encode('utf-8') if rel.as_posix() == 'info.nut' else file.read_bytes()
        if not (target / rel).is_file() or (target / rel).read_bytes() != new_bytes:
            changed.append(rel.as_posix())
            if apply:
                (target / rel).parent.mkdir(parents=True, exist_ok=True)
                (target / rel).write_bytes(new_bytes)
    return {
        'selected_20x10': {k: winner[k] for k in (
            'suite', 'name', 'ratio_pct', 'opex_profit_mean',
            'aaa_profit_mean', 'source_bundle_sha256', 'campaign')},
        'source_bundle_path': str(bundle),
        'source_files': len(src),
        'files_to_add_or_update': changed,
        'default_settings': defaults,
        'explicit_old_settings_preserved': True,
        'c121_fullscan_frozen_source_sha256': sha(source / 'air_economics_c121_fullscan.nut'),
        'applied_to_isolated_worktree': apply,
        'not_yet_proven': ('A new default has not been runtime-validated; separate '
                           'tests, SaveLoad, and smoke are required before any master merge.'),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository', required=True, type=Path)
    ap.add_argument('--worktree', required=True, type=Path)
    ap.add_argument('--result', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    report = json.loads(args.result.read_text('utf-8'))
    manifest = promote(args.repository.resolve(), args.worktree.resolve(),
                       report, apply=args.apply)
    args.output.write_text(json.dumps(manifest, indent=2) + '\n', 'utf-8')
    print('PROMOTION', 'APPLIED' if args.apply else 'DRY_RUN',
          manifest['selected_20x10']['suite'],
          manifest['selected_20x10']['name'],
          'FILES', len(manifest['files_to_add_or_update']))


if __name__ == '__main__':
    main()
