"""Read verified final save PLYR fiscal posts without thousands of monthly saves.

Only at 1974-12-01, for all 80 paired games, no individual purchase event or
rail/air CAPEX allocation can be inferred. Archive checksums and game mapping
come from frozen campaign manifest. Useful even while full physical inventory
analysis is pending.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from sweeps.estim31_real_accounts_from_saves_20261030 import read_sav, NAMES


def analyze_final(bundle, campaign):
    result_dir = bundle / 'results'
    manifest = json.loads((result_dir / (campaign + '.manifest.json')).read_text('utf-8'))
    summary = json.loads((result_dir / (campaign + '.json')).read_text('utf-8'))
    if len(manifest['games']) != 80 or len(summary['games']) != 80:
        raise ValueError('Not 80 games')
    statuses = {g['game_id']: g for g in summary['games']}
    amounts = defaultdict(list)
    for index, game in enumerate(manifest['games']):
        health = statuses.get(game['game_id'])
        if not health or not health['game_ok'] or health['game_status'] != 'complete':
            raise ValueError('Unhealthy or missing simulation ' + game['game_id'])
        archive_dir = result_dir / (campaign + '_saves') / str(index)
        archive = json.loads((archive_dir / 'archive.json').read_text('utf-8'))
        if len(archive['savegames']) < 60:
            raise ValueError('Incomplete monthly save archive')
        last = archive['savegames'][-1]
        sav = archive_dir / last['path']
        if hashlib.sha256(sav.read_bytes()).hexdigest() != last['sha256']:
            raise ValueError('Save SHA mismatch ' + str(sav))
        date, players = read_sav(sav)
        if date.isoformat() != '1974-12-01':
            raise ValueError('Unexpected terminal save date ' + str(date))
        for slot, name in (('0', 'OpexAI'), ('1', 'AAAHogEx')):
            if slot not in players:
                raise ValueError('Missing company ' + str(slot))
            amounts[(game['policy_id'], name)].append(players[slot])
    outcome = {}
    for (policy, name), data in sorted(amounts.items()):
        if len(data) != 40:
            raise ValueError('Insufficient paired seeds')
        outcome[f'{policy}:{name}'] = {field: mean(row[i] for row in data)
                                       for i, field in enumerate(NAMES)}
    return dict(campaign=campaign, source_sha256=summary['source_bundle_sha256'],
                cutoff='1974-12-01', healthy_games=80,
                category_mean_net_postings=outcome,
                note=('OpenTTD PLYR net 1974 YTD accounts through Dec 1, not gross cash '
                      'spent per line or engine. Construction includes all modes; '
                      'vehicle net purchases less sale proceeds across all modes; '
                      'Other includes statues and unrelated expenses.'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bundle', required=True, type=Path)
    ap.add_argument('--campaign', required=True)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    data = analyze_final(args.bundle.resolve(), args.campaign)
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('FINANCIAL_POSTINGS', data['campaign'], '80/80 verified', data['category_mean_net_postings'])


if __name__ == '__main__':
    main()
