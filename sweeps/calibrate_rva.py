"""Offline RVA diagnostic. Frozen split by seed, never by correlated log row.

Old V216 logs have aggregated coverage, not the complete per-tile inventory.
Validate an explicitly labelled aggregate projection, not invented tile truth.
Calibration is a measured future station rating; no global revenue multiplier.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics

from analyze_v216 import parse_log, error_attribution_b
from rva_demand import station_allocation


def projected_share(row, rating_pct):
    """Aggregate approximation: one own station, one rival on adv-only tiles.

    Rival rating is unreadable: equal-rating scenario, NOT an API observation.
    Old own+adversary overlap and own station sums are not available.
    """
    shares = []
    for end in ('a', 'b'):
        p, own, adv, rating = [row.get(f'g.{end}_{k}')
                               for k in ('prod', 'own', 'adv', 'rown')]
        if None in (p, own, adv, rating) or p <= 0:
            return None
        new = dict(station='new', owner='us', rating_raw=rating_pct * 255 / 100)
        own_st = dict(station='old', owner='us', rating_raw=rating * 255 / 100)
        rival = dict(station='rival', owner='them', rating_raw=new['rating_raw'])
        free = p - own - adv
        if free < 0:
            return None
        q = 0
        for n, old in ((free, []), (own, [own_st]), (adv, [rival])):
            q += n * station_allocation(1, [*old, new])['new']
        shares.append(q / p)
    return statistics.mean(shares)


def errors(rows):
    if not rows:
        return {'n': 0, 'mae_annual': None, 'bias_annual': None, 'wape': None}
    return {'n': len(rows), 'mae_annual': statistics.mean(abs(p-y) for p,y in rows),
            'bias_annual': statistics.mean(p-y for p,y in rows),
            'wape': sum(abs(p-y) for p,y in rows) / sum(abs(y) for p,y in rows)
                    if any(y for _,y in rows) else None}


def calibrate(paths):
    paths = sorted(map(Path, paths))
    seeds = sorted({int(re.search(r'_seed(\d+)_', p.name)[1]) for p in paths})
    train, test = set(seeds[::2]), set(seeds[1::2])
    games, sources, ratings = [], [], []
    for path in paths:
        seed = int(re.search(r'_seed(\d+)_', path.name)[1])
        game = parse_log(path)
        games.append((path, seed, game))
        sources.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        if seed in train:
            # Pool only rail-only stations, avoiding airport ratings on joined facilities.
            ratings.extend(r['rating_PASS'] for r in game['station_flow']
                if r.get('rail') == 1 and r.get('air') == 0 and r.get('rating_PASS', -1) >= 0)
    rating = statistics.median(ratings) if ratings else None
    rows = []
    for path, seed, game in games:
        for line in error_attribution_b([game]).get('PASS', {}).get('lines', []):
            d = line['decomp']
            share = projected_share(d, rating) if rating is not None else None
            offered, capacity = d.get('c.offered'), d.get('c.monthlyCapacity')
            old_carried = d.get('c.carried')
            monthly = d.get('c.monthly')
            predicted = None
            if share is not None and None not in (offered, capacity, old_carried, monthly) and old_carried > 0:
                # SAME baseline cycle, to isolate the demand allocation diagnostic.
                new_carried = min(monthly * share, capacity)
                predicted = line['pred_rev'] * new_carried / old_carried
            rows.append({'source': path.name, 'campaign': path.parent.name, 'seed': seed,
                         'fold': 'train' if seed in train else 'test',
                         'line': line['line'], 'actual_annual': line['real_rev'],
                         'reference_annual': line['pred_rev'], 'estimated_annual': predicted,
                         'share': share, 'coverage': 'aggregate_projection_not_tile_validation'})
    metrics = {}
    for fold in ('train', 'test'):
        selected = [r for r in rows if r['fold'] == fold and r['estimated_annual'] is not None]
        metrics[fold] = {k: errors([(r[field], r['actual_annual']) for r in selected])
                        for k, field in [('baseline', 'reference_annual'), ('estimated', 'estimated_annual')]}
    return {'schema': 1, 'split': {'rule': 'sorted_unique_seeds_alternating_train_then_test',
            'train': sorted(train), 'test': sorted(test)},
            'rating_pct': rating, 'rating_observations': len(ratings),
            'rating_status': 'empirical_training_station_median_not_deployed',
            'local_volume_error': None,
            'local_volume_error_status': 'old_logs_lack_tile_weights_and_local_deliveries',
            'metric': 'annual_line_receipts_proxy_not_company_gain',
            'sources': sources, 'metrics': metrics, 'rows': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directories', nargs='+', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    paths = [f for d in args.directories for f in d.glob('*.log*')]
    args.out.write_text(json.dumps(calibrate(paths), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
