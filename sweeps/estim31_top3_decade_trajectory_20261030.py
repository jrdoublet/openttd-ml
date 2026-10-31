"""Annual profit/cash/network trajectories of verified ESTIM31 top-three 20x10s.

All ratios divide TWO annual means from the SAME 20-seed candidate policy,
not the mean of per-seed ratios and not an AAA baseline from another run.
Only complete candidates accepted by the strict 20x10 verifier are reported.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from sweeps.estim31_top3_20x10_20261030 import (
    SEEDS20, SUITES_ALL, YEARS, analyze)


def company_mean(rows):
    return {
        'profit_year': mean(r['profit_year'] for r in rows),
        'cash': mean(r['money'] for r in rows),
        'current_loan': mean(r['current_loan'] for r in rows),
        'aircraft_stock': mean(r['air_primary_vehicles'] for r in rows),
        'train_stock': mean(r['primary_vehicles_by_mode']['rail'] for r in rows),
        'airport_count': mean(r['air_airports'] for r in rows),
        'airport_towns': mean(r['airport_towns_opex_present'] for r in rows),
        'air_engine_stock_223': mean(r.get('air_engine_counts', {}).get('223', 0)
                                     for r in rows),
        'air_engine_stock_228': mean(r.get('air_engine_counts', {}).get('228', 0)
                                     for r in rows),
        'air_engine_stock_220': mean(r.get('air_engine_counts', {}).get('220', 0)
                                     for r in rows),
    }


def summarize_year(ours, theirs):
    if len(ours) != len(theirs) or not ours:
        raise ValueError('Incomplete annual seed pair')
    a, b = company_mean(ours), company_mean(theirs)
    if b['profit_year'] <= 0:
        raise ValueError('AAA annual profit nonpositive')
    return {'opex': a, 'aaa': b,
            'ratio_of_means_pct': 100 * a['profit_year'] / b['profit_year'],
            'samples': len(ours)}


def trajectory(repo, frozen):
    verified = analyze(repo, frozen)
    output = {
        'criterion': '100 * mean20(OpexAI annual profit_year) / mean20(AAAHogEx annual profit_year), same duel',
        'qualified_candidates': [],
        'pending': verified['not_yet_qualified'],
        'winner': verified['winner']['name'] if verified['winner'] else None,
    }
    for candidate in verified['ranked_healthy_20x10']:
        suite, name = candidate['suite'], candidate['name']
        folder, prefix = SUITES_ALL[suite]
        root = repo / 'results' / folder / name / 'results'
        path = root / (candidate['campaign'] + '.jsonl')
        arms = {'reference': defaultdict(dict), prefix + '_' + name: defaultdict(dict)}
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                policy, date = row.get('duel_policy_id'), row.get('date')
                if policy not in arms or date not in YEARS:
                    continue
                company, seed, repeat = row.get('run', (None, None, None))
                if company not in ('OpexAI', 'AAAHogEx') or seed not in SEEDS20 or repeat != 0:
                    continue
                key = (company, seed)
                if key in arms[policy][date]:
                    raise ValueError('Duplicated annual pair')
                arms[policy][date][key] = row
        yearly = []
        for year in YEARS:
            policies = {}
            for policy, dates in arms.items():
                data = dates[year]
                if set(data) != {(company, seed) for company in ('OpexAI', 'AAAHogEx')
                                 for seed in SEEDS20}:
                    raise ValueError('Annual seed/date coverage mismatch')
                ours = [data[('OpexAI', seed)] for seed in SEEDS20]
                theirs = [data[('AAAHogEx', seed)] for seed in SEEDS20]
                policies['off' if policy == 'reference' else 'variant'] = summarize_year(ours, theirs)
            yearly.append({'date': year, **policies})
        if abs(yearly[-1]['variant']['ratio_of_means_pct'] - candidate['ratio_pct']) > 1e-8:
            raise ValueError('1979 trend and qualified winning metric disagree')
        output['qualified_candidates'].append({
            'suite': suite, 'name': name, 'campaign': candidate['campaign'],
            'source_bundle_sha256': candidate['source_bundle_sha256'],
            'years': yearly,
        })
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository', type=Path, required=True)
    ap.add_argument('--frozen', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    frozen = json.loads(args.frozen.read_text('utf-8'))
    data = trajectory(args.repository.resolve(), frozen)
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    for row in data['qualified_candidates']:
        print('TRAJECTORY_OK', row['suite'], row['name'],
              row['years'][-1]['variant']['ratio_of_means_pct'])
    print('PENDING', len(data['pending']))


if __name__ == '__main__':
    main()
