#!/usr/bin/env python3
"""Comparer les duels N=2 gate et fast-path sur les mêmes graines.

Les comparaisons inter-bundles sont descriptives : la reference OFF peut
diverger entre sources/ordonnancements, donc pas de causalite attribuable.
"""

import argparse
import json
from pathlib import Path
from statistics import mean, median


BASE = Path('results')
OLD = BASE / 'rail_n2_gate_gain_short_40x3_20261009_r2.jsonl'
NEW = BASE / 'rail_n2_gate_fastpath_diag_5x3_20261009_r1.jsonl'


def load(path):
    result = {}
    for raw in path.open(encoding='utf-8'):
        p = json.loads(raw)
        run = p.get('run')
        if not run or run[0] != 'OpexAI' or p['date'] != '1972-12-01':
            continue
        result[(p['duel_policy_id'], run[1])] = p
    return result


def summarize(rows):
    return {'mean': mean(rows), 'median': median(rows),
            'wins': sum(x > 0 for x in rows),
            'losses': sum(x < 0 for x in rows),
            'ties': sum(x == 0 for x in rows)}


def analyze(old_path=OLD, new_path=NEW, variant_policy='gate_fastpath'):
    old, new = load(old_path), load(new_path)
    seeds = sorted({s for policy, s in new if policy == 'reference'})
    per_seed = []
    for seed in seeds:
        old_off, old_gate = old[('reference', seed)], old[('gate', seed)]
        new_off, new_gate = new[('reference', seed)], new[(variant_policy, seed)]
        row = {'seed': seed}
        for metric in ('profit_year', 'company_value'):
            row[metric] = {'old_off': old_off[metric], 'new_off': new_off[metric],
                           'old_gate': old_gate[metric], 'new_gate': new_gate[metric],
                           'old_gate_delta': old_gate[metric] - old_off[metric],
                           'new_gate_delta': new_gate[metric] - new_off[metric],
                           'fastpath_vs_old_gate': new_gate[metric] - old_gate[metric]}
        per_seed.append(row)
    reference_mismatch_seeds = [row['seed'] for row in per_seed if any(
        row[m]['old_off'] != row[m]['new_off'] for m in ('profit_year', 'company_value'))]
    return {
        'note': ('Comparaison descriptive sur %s graines entre deux bundles figes : '
                 'seuls les deltas apparies au sein de chaque bundle sont qualifies '
                 'selon les regles propres de leur campagne.' % len(seeds)),
        'seeds': seeds, 'pairs': per_seed,
        'strict_reference_parity': not reference_mismatch_seeds,
        'reference_mismatch_seeds': reference_mismatch_seeds,
        'statistics': {m: {
            field: summarize([row[m][field] for row in per_seed])
            for field in ('old_gate_delta','new_gate_delta','fastpath_vs_old_gate')}
            for m in ('profit_year','company_value')},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-jsonl', type=Path, default=OLD)
    parser.add_argument('--new-jsonl', type=Path, default=NEW)
    parser.add_argument('--variant-policy-id', default='gate_fastpath')
    parser.add_argument('--out', type=Path, default=BASE / 'rail_n2_gate_fastpath_comparison_5x3_20261009.json')
    args = parser.parse_args()
    target = args.out
    if target.exists():
        raise SystemExit('Refusing overwrite ' + str(target))
    report = analyze(args.old_jsonl, args.new_jsonl, args.variant_policy_id)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Strict OFF parity:', report['strict_reference_parity'])
    print('profit_year:', report['statistics']['profit_year'])
    print('Per seed:')
    for item in report['pairs']:
        print(item['seed'], item['profit_year'])
