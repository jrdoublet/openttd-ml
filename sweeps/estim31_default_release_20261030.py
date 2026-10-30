"""Prepare the user-authorized ESTIM31 default from the 20x10 winner.

Write-once deployable source BUNDLE, separate from the dirty shared master.
The original validated winner remains immutable. Only info.nut defaults and
their human-readable descriptions differ in the release copy; no other source
can be silently regenerated, tuned, or taken from another finalist.
The script does NOT claim to have deployed the production /ai tree.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from sweeps.estim31_top3_20x10_20261030 import SUITES_ALL

SETTINGS = {'estim_unifie': 31, 'eb14_progressive': 3, 'probes': 2}
PATTERN = r'AddSetting\(\{\s*name\s*=\s*"(?P<name>[a-z0-9_]+)"(?P<body>.*?)\}\);'


def make_default_info(source):
    """Only rewrite the three frozen option records, with strict guards."""
    found = {}

    def replace(match):
        name = match.group('name')
        if name not in SETTINGS:
            return match.group(0)
        if name in found:
            raise ValueError('Duplicate public setting ' + name)
        found[name] = 1
        body = match.group('body')
        for key in ('easy_value', 'medium_value', 'hard_value', 'custom_value'):
            expr = rf'\b({key}\s*=\s*)0\b'
            body, count = re.subn(expr, rf'\g<1>{SETTINGS[name]}', body)
            if count != 1:
                raise ValueError(f'{name}: expected one zero for {key}; got {count}')
        expr = r'\b(default_value\s*=\s*)0\b'
        body, count = re.subn(expr, rf'\g<1>{SETTINGS[name]}', body)
        if name == 'probes':
            if count != 0:
                raise ValueError('Unexpected explicit probes default')
            # Existing four difficulty defaults completely define OpenTTD's default.
        elif count != 1:
            raise ValueError(f'{name}: missing explicit default')
        if name == 'estim_unifie':
            body = body.replace('0 = historical (default)', '0 = historical, 31 = default')
        if name == 'eb14_progressive':
            body = body.replace('0=off (default)', '0=off, 3=default')
        if name == 'probes':
            body = body.replace('0 none (default)', '0 none, 2 signs (default)')
        return match.group(0).replace(match.group('body'), body, 1)

    new_info = re.sub(PATTERN, replace, source, flags=re.S)
    if set(found) != set(SETTINGS):
        raise ValueError('Missing public default settings: ' + str(set(SETTINGS) - set(found)))
    new_info = new_info.replace(
        'Defaut publication 0 = carte vierge ; les harnais injectent probes=2.',
        'Defaut public 2 = panneaux ; valeur identique aux duels 20x10 de promotion.')
    if new_info == source:
        raise ValueError('No default changes were made')
    return new_info


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(repo, chosen, output):
    if output.exists():
        raise FileExistsError('Write-once default release already exists: ' + str(output))
    winner = chosen.get('winner')
    if not winner or chosen.get('not_yet_qualified') or len(chosen.get('ranked_healthy_20x10', [])) != 3:
        raise ValueError('Cannot choose a default before three healthy 20x10 duels')
    if winner['health'] != '40/40 complete' or winner['source_bundle_sha256'] not in (
            item['source_bundle_sha256'] for item in chosen['ranked_healthy_20x10']):
        raise ValueError('Winning source / simulation health not verified')
    suite, name = winner['suite'], winner['name']
    if suite not in SUITES_ALL:
        raise ValueError('Unknown qualifying suite')
    folder, _ = SUITES_ALL[suite]
    parent = repo / 'results' / folder / name
    if not (parent / 'ai/OpexAI/info.nut').is_file():
        raise ValueError('No frozen AI bundle')
    new_info = make_default_info((parent / 'ai/OpexAI/info.nut').read_text('utf-8'))
    for part in ('ai', 'ai_libraries', 'sweeps'):
        shutil.copytree(parent / part, output / part)
    for filename in ('Dockerfile', 'requirements.txt', 'requirements-ml.txt'):
        shutil.copy2(parent / filename, output / filename)
    dest_info = output / 'ai/OpexAI/info.nut'
    dest_info.write_text(new_info, encoding='utf-8')
    expected_files = {p.relative_to(parent).as_posix(): digest(p)
                      for p in (parent / 'ai').rglob('*') if p.is_file()}
    actual_files = {p.relative_to(output).as_posix(): digest(p)
                    for p in (output / 'ai').rglob('*') if p.is_file()}
    if expected_files.keys() != actual_files.keys():
        raise ValueError('Deployable AI files differ from winning source set')
    nonidentity = {name for name in actual_files
                   if actual_files[name] != expected_files[name]}
    if nonidentity != {'ai/OpexAI/info.nut'}:
        raise ValueError('Unexpected source modification in release: ' + str(nonidentity))
    identity = {'winner': {'suite': suite, 'name': name,
                           'ratio_20x10_pct': winner['ratio_pct'],
                           'source_bundle_sha256': winner['source_bundle_sha256']},
                'settings_promoted': SETTINGS,
                'source_parent': str(parent),
                'changed_only': ['ai/OpexAI/info.nut'],
                'frozen_info_sha256': expected_files['ai/OpexAI/info.nut'],
                'release_info_sha256': actual_files['ai/OpexAI/info.nut'],
                'ai_file_count': len(expected_files),
                'deployable_source_ready': True,
                'production_ai_updated': False,
                'important': ('Releasing a candidate does not touch shared dirty master. '
                              'Production integration, smoke and fullsuite are separate.') }
    (output / 'release_manifest.json').write_text(
        json.dumps(identity, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return identity


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository', type=Path, required=True)
    ap.add_argument('--analysis', type=Path, required=True)
    ap.add_argument('--destination', type=Path, required=True)
    args = ap.parse_args()
    result = prepare(args.repository.resolve(),
                     json.loads(args.analysis.read_text('utf-8')),
                     args.destination.resolve())
    print('DEFAULT_RELEASE_READY', result['winner'],
          'files=', result['ai_file_count'], 'production_ai_updated=False')


if __name__ == '__main__':
    main()
