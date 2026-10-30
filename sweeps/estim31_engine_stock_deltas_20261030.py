"""Monthly physical engine-stock changes: lower bounds, NEVER gross purchases.

A stock can rise and fall between two monthly snapshots. Positive differences
are a minimum of net appearances observed at snapshots, not actual buy events,
cash spending, or a substitute for an audited journal of transactions.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from sweeps.estim31_joint_newgrid_analyse_20261030 import SEEDS40

MONTHS = tuple(f'{year}-{month:02d}-01' for year in range(1970, 1975)
               for month in range(1, 13))


def summarize(rows, policy, source_sha, seeds=SEEDS40):
    snapshots = defaultdict(dict)
    for row in rows:
        if row.get('duel_policy_id') != policy or row.get('run', [None])[0] != 'OpexAI':
            continue
        _, seed, repeat = row['run']
        if seed not in seeds or repeat != 0 or row.get('date') not in MONTHS:
            continue
        if row.get('source_bundle_sha256') != source_sha:
            raise ValueError('Snapshot source hash mismatch')
        if row['date'] in snapshots[seed]:
            raise ValueError('Duplicate Opex monthly snapshot')
        snapshots[seed][row['date']] = row
    if set(snapshots) != set(seeds):
        raise ValueError('Missing seeds in physical snapshots')
    positive, negative, last = Counter(), Counter(), Counter()
    for seed in seeds:
        if set(snapshots[seed]) != set(MONTHS):
            raise ValueError('Missing month in seed ' + str(seed))
        previous = {}
        for month in MONTHS:
            observed = snapshots[seed][month].get('air_engine_counts') or {}
            current = {str(key): int(value) for key, value in observed.items()}
            for engine in previous.keys() | current.keys():
                delta = current.get(engine, 0) - previous.get(engine, 0)
                if delta > 0:
                    positive[engine] += delta
                if delta < 0:
                    negative[engine] -= delta
            previous = current
        last.update(previous)
    return {'seeds': len(seeds), 'months_each': len(MONTHS),
            'policy': policy, 'source_sha256': source_sha,
            'positive_observed_stock_steps': dict(positive),
            'negative_observed_stock_steps': dict(negative),
            'final_stock': dict(last),
            'limitations': ('Positive monthly stock differences are LOWER BOUNDS '
                            'of observed appearances, not gross physical purchases, '
                            'invoices or cash transfers. Intramonth churn is hidden.')}


def analyze(report_path, jsonl_path, policy):
    report = json.loads(report_path.read_text('utf-8'))
    if (len(report.get('games', [])) != 80 or report.get('failed_runs')
            or any(not g.get('game_ok') or g.get('game_status') != 'complete'
                   for g in report['games'])):
        raise ValueError('Incomplete or unhealthy 40x5')
    with jsonl_path.open(encoding='utf-8') as inp:
        return summarize((json.loads(line) for line in inp), policy,
                         report['source_bundle_sha256'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--jsonl', required=True, type=Path)
    ap.add_argument('--policy', required=True)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    result = analyze(args.report, args.jsonl, args.policy)
    args.output.write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print('ENGINE_STOCK_STEPS', result)


if __name__ == '__main__':
    main()
