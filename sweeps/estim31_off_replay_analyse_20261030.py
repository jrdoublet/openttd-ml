"""Compare unchanged OFF trajectories between repeats, without promoting a replay.

The source and image digests are checked independently of the trajectory.  This
comparison detects non-reproducibility but cannot assign its physical cause.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

FIELDS = ('profit_year', 'company_value', 'money', 'air_primary_vehicles',
          'air_airports', 'observed_opcodes_total', 'air_engine_counts')
SEEDS = (999, 2026)
COMPANIES = ('OpexAI', 'AAAHogEx')
DATES = tuple(f'{year}-{month:02d}-01' for year in range(1970, 1975)
              for month in range(1, 13))


def evaluate(jsonl, summary):
    info = json.loads(summary.read_text('utf-8'))
    if info.get('failed_runs') or len(info.get('games', [])) != 4:
        raise ValueError('Incomplete or failed 2 seeds x 2 repeats summary')
    if any(not game.get('game_ok') or game.get('game_status') != 'complete'
           for game in info['games']):
        raise ValueError('Unhealthy OFF replay')
    sha = info['source_bundle_sha256']
    records = {}
    for line in jsonl.read_text('utf-8').splitlines():
        row = json.loads(line)
        if row.get('date') not in DATES:
            continue
        if row.get('duel_policy_id') != 'reference':
            raise ValueError('Unexpected policy')
        if row.get('source_bundle_sha256') != sha:
            raise ValueError('Source digest disagreement')
        company, seed, repeat = row['run']
        key = (company, seed, repeat, row['date'])
        if key in records:
            raise ValueError(f'Duplicate checkpoint {key}')
        records[key] = row
    expected = {(co, seed, repeat, date)
                for co in COMPANIES for seed in SEEDS
                for repeat in (0, 1) for date in DATES}
    if set(records) != expected:
        raise ValueError(f'Missing/unexpected checkpoints: missing={len(expected-set(records))}, '
                         f'excess={len(set(records)-expected)}')
    drift = []
    for company in COMPANIES:
        for seed in SEEDS:
            for date in DATES:
                a = records[(company, seed, 0, date)]
                b = records[(company, seed, 1, date)]
                for field in FIELDS:
                    if a.get(field) != b.get(field):
                        drift.append(dict(company=company, seed=seed, date=date,
                                          field=field, repeat0=a.get(field),
                                          repeat1=b.get(field)))
    counts = Counter((row['company'], row['seed']) for row in drift)
    return dict(source_bundle_sha256=sha, games=4, expected_comparisons=2*2*60*len(FIELDS),
                mismatches=len(drift), by_company_seed={f'{k[0]}_{k[1]}': v
                for k, v in sorted(counts.items())}, first_mismatch=drift[0] if drift else None,
                field_counts=dict(Counter(row['field'] for row in drift)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=(1, 8), default=1)
    args = parser.parse_args()
    campaign = f'estim31_off_replay_seed999_2026_{args.workers}worker_20261030'
    result = args.bundle / 'results'
    report = evaluate(result / f'{campaign}.jsonl', result / f'{campaign}.json')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
