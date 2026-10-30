"""Read real OpenTTD PLYR 1979 fiscal postings from all 40 final saved games.

Posts are net YTD accounting entries (not gross aircraft purchases or
per-line CAPEX). All saves must have verified SHA, 1979-12-01, correct
campaign/policy/seed identity and healthy 20x10 report.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from sweeps.estim31_real_accounts_from_saves_20261030 import read_sav, NAMES
from sweeps.estim31_top3_20x10_20261030 import SEEDS20


def analyze_final(bundle, campaign):
    result_dir = bundle / 'results'
    manifest = json.loads((result_dir / (campaign + '.manifest.json')).read_text('utf-8'))
    report = json.loads((result_dir / (campaign + '.json')).read_text('utf-8'))
    if (len(manifest.get('games', [])) != 40 or len(report.get('games', [])) != 40
            or report.get('failed_runs')
            or set(report.get('seeds', [])) != set(SEEDS20)
            or report.get('expected_last_checkpoint') != '1979-12-01'):
        raise ValueError('Incomplete 20x10 campaign or seed provenance')
    statuses = {g['game_id']: g for g in report['games']}
    postings = defaultdict(list)
    policy_seeds = defaultdict(set)
    for index, game in enumerate(manifest['games']):
        observed = statuses.get(game['game_id'])
        if (not observed or observed.get('source_bundle_sha256')
                != report.get('source_bundle_sha256')
                or not observed.get('game_ok') or observed.get('game_status') != 'complete'
                or observed.get('seed') not in SEEDS20
                or observed.get('repeat') != 0):
            raise ValueError('Unhealthy or foreign game ' + game['game_id'])
        policy = observed['policy_id']
        seed = observed['seed']
        if seed in policy_seeds[policy]:
            raise ValueError('Duplicated seed for policy')
        policy_seeds[policy].add(seed)
        archive = result_dir / (campaign + '_saves') / str(index)
        entries = json.loads((archive / 'archive.json').read_text('utf-8'))['savegames']
        if len(entries) < 120:
            raise ValueError('Incomplete monthly save archive')
        last = entries[-1]
        path = archive / last['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != last['sha256']:
            raise ValueError('Final save archive SHA mismatch')
        date, companies = read_sav(path)
        if date.isoformat() != '1979-12-01':
            raise ValueError('Final account date mismatch')
        for slot, name in (('0', 'OpexAI'), ('1', 'AAAHogEx')):
            if slot not in companies:
                raise ValueError('Missing company in PLYR final save')
            postings[policy, name].append(companies[slot])
    if (len(policy_seeds) != 2 or any(seeds != set(SEEDS20)
                                      for seeds in policy_seeds.values())):
        raise ValueError('Missing identical 20-seed policy groups')
    outcome = {}
    for (policy, company), rows in postings.items():
        if len(rows) != 20:
            raise ValueError('Not twenty accounting rows per policy/company')
        outcome[f'{policy}:{company}'] = {
            field: mean(row[i] for row in rows) for i, field in enumerate(NAMES)}
    return {'campaign': campaign, 'cutoff': '1979-12-01',
            'source_bundle_sha256': report['source_bundle_sha256'],
            'healthy_games': 40, 'paired_seeds': 20,
            'mean_1979_ytd_net_postings': outcome,
            'limitations': ('Yearly PLYR posts are real NET entries: construction ALL modes; '
                            'vehicles purchases LESS sales ALL modes; Other includes '
                            'town actions, not solely statues. Not gross acquisition costs.')}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bundle', type=Path, required=True)
    ap.add_argument('--campaign', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    data = analyze_final(args.bundle.resolve(), args.campaign)
    args.output.write_text(json.dumps(data, indent=2) + '\n', 'utf-8')
    print('PLYR_20X10', data['campaign'], data['healthy_games'], data['paired_seeds'])


if __name__ == '__main__':
    main()
