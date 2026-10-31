"""Freeze 40x5 top three, then verify independent, healthy 20x10 duels.

The only economic metric is 100 * mean20(OpexAI profit_year at 1979-12-01)
                              / mean20(AAAHogEx profit_year at 1979-12-01).
No 40x5 values, old AAA denominators, CI, Wilcoxon or value guard are used
to select the ten-year winner. A frozen 40x5 shortlist prevents moving ranks.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

from sweeps.estim31_joint_newgrid_analyse_20261030 import SEEDS40
from sweeps.estim31_v161_newrank_20261030 import SUITES

SUITES_ALL = {'v161': ('estim31_v161_safe20261030', 'estim31v161'), **SUITES}
SEEDS20 = tuple(SEEDS40[:20])
END = '1979-12-01'
YEARS = tuple(f'{year}-12-01' for year in range(1970, 1980))
POLICIES = ('reference', 'variant')
CAMPAIGN_PREFIX = {
    'v161': 'estim31v161', 'v161cap': 'estim31vcap',
    'v161coeff': 'estim31vcoef', 'v161policy': 'estim31vp',
    'noupper': 'estim31nohi', 'rail1970': 'estim31r1970',
    'capcombo': 'estim31capco',
}


def freeze(top5_rank):
    qualified = top5_rank['ranked']
    if len(qualified) < 3:
        raise ValueError('At least three healthy 40x5 finalists required')
    selected = []
    for row in qualified[:3]:
        if (row['health'] != '80/80 complete'
                or len(row.get('pairs', {})) != 40
                or not row.get('source_bundle_sha256')):
            raise ValueError('Unhealthy 40x5 finalist')
        selected.append({'suite': row['suite'], 'name': row['name'],
                         'ratio_40x5_pct': row['ratio_pct'],
                         'source_bundle_sha256': row['source_bundle_sha256'],
                         'configuration': row.get('configuration')})
    return {'criterion_5y': top5_rank['criterion'],
            'criterion_10y': '100 * mean20(OpexAI 1979-12-01 profit_year) / mean20(AAAHogEx 1979-12-01 profit_year)',
            'locked_40x5_ranking': selected,
            'seeds20': list(SEEDS20),
            'runner_years': 10,
            'runner_workers_max': 8,
            'default_decision': 'Highest healthy 20x10 ratio only, user explicitly authorized default change'}


def analyze_one(repo, finalist):
    suite, name = finalist['suite'], finalist['name']
    folder, prefix = SUITES_ALL[suite]
    if prefix != CAMPAIGN_PREFIX[suite]:
        raise ValueError('Unknown prefix for suite')
    root = repo / 'results' / folder / name / 'results'
    policy = f'{prefix}_{name}'
    campaign = f'estim31ten_{prefix}_{name}_20x10_20261030'
    report_path = root / (campaign + '.json')
    jsonl_path = root / (campaign + '.jsonl')
    manifest_path = root / (campaign + '.manifest.json')
    identity = {'suite': suite, 'name': name,
                'ratio_40x5_pct': finalist['ratio_40x5_pct'],
                'source_bundle_sha256': finalist['source_bundle_sha256']}
    if not all(p.is_file() for p in (report_path, jsonl_path, manifest_path)):
        return None, {**identity, 'reason': 'result incomplete'}
    report = json.loads(report_path.read_text('utf-8'))
    if (report.get('campaign_id') != campaign or report.get('policy_id') != 'reference'
            or report.get('years') != 10 or report.get('start_year') != 1970
            or report.get('repeats') != 1 or report.get('map_size') != 8
            or report.get('expected_last_checkpoint') != END
            or len(report.get('seeds', [])) != 20
            or set(report['seeds']) != set(SEEDS20)
            or report.get('source_bundle_sha256') != finalist['source_bundle_sha256']
            or hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            != report.get('manifest_sha256')):
        return None, {**identity, 'reason': 'source/campaign/manifest/horizon mismatch'}
    policies = report.get('policies', [])
    if len(policies) != 2 or {p.get('id') for p in policies} != {'reference', policy}:
        return None, {**identity, 'reason': 'policy roster mismatch'}
    try:
        explicit = {p['id']: dict(p['explicit_settings']) for p in policies}
    except (KeyError, TypeError, ValueError):
        return None, {**identity, 'reason': 'invalid policy settings'}
    if (explicit['reference'] != {'probes': 2}
            or explicit[policy].get('probes') != 2
            or explicit[policy].get('estim_unifie') != 31):
        return None, {**identity, 'reason': 'reference or variant settings altered'}
    games = report.get('games', [])
    if report.get('failed_runs') or len(games) != 40:
        return None, {**identity, 'reason': 'not 40 healthy games'}
    keys = set()
    for game in games:
        key = (game.get('seed'), game.get('policy_id'), game.get('repeat'))
        if (key in keys or game.get('campaign_id') != campaign
                or game.get('source_bundle_sha256') != finalist['source_bundle_sha256']
                or game.get('expected_last_checkpoint') != END
                or not game.get('game_ok') or game.get('game_status') != 'complete'
                or any(not game.get('companies', {}).get(c, {}).get('run_ok')
                       or not game['companies'][c].get('horizon_complete')
                       or game['companies'][c].get('status') != 'complete'
                       for c in ('OpexAI', 'AAAHogEx'))):
            return None, {**identity, 'reason': 'game health or identity mismatch'}
        keys.add(key)
    if keys != {(seed, arm, 0) for seed in SEEDS20 for arm in ('reference', policy)}:
        return None, {**identity, 'reason': 'unpaired seed or duplicated policy'}
    arms = {'reference': {}, policy: {}}
    with jsonl_path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            p = row.get('duel_policy_id')
            if p not in arms or row.get('date') not in YEARS:
                continue
            company, seed, repeat = row.get('run', [None, None, None])
            if seed not in SEEDS20 or repeat != 0 or company not in ('OpexAI', 'AAAHogEx'):
                continue
            key = (seed, company, row['date'])
            if key in arms[p]:
                return None, {**identity, 'reason': 'duplicated checkpoint'}
            if (row.get('campaign_id') != campaign or row.get('source_bundle_sha256')
                    != finalist['source_bundle_sha256']):
                return None, {**identity, 'reason': 'checkpoint source/campaign mismatch'}
            arms[p][key] = row
    target = {(s, c, y) for s in SEEDS20
              for c in ('OpexAI', 'AAAHogEx') for y in YEARS}
    if any(set(arm) != target for arm in arms.values()):
        return None, {**identity, 'reason': 'annual checkpoints incomplete'}
    def summarize(arm):
        ours = [arm[(seed, 'OpexAI', END)] for seed in SEEDS20]
        theirs = [arm[(seed, 'AAAHogEx', END)] for seed in SEEDS20]
        a = mean(row['profit_year'] for row in ours)
        b = mean(row['profit_year'] for row in theirs)
        if b <= 0:
            raise ValueError('Non-positive AAA profit')
        return {'opex_profit_mean': a, 'aaa_profit_mean': b,
                'ratio_pct': 100.0 * a / b,
                'paired_profit_difference_mean': a - b,
                'opex_wins': sum(x['profit_year'] > y['profit_year']
                                 for x, y in zip(ours, theirs)),
                'opex_cash_mean': mean(x['money'] for x in ours),
                'aaa_cash_mean': mean(y['money'] for y in theirs),
                'opex_loan_mean': mean(x['current_loan'] for x in ours),
                'aircraft_stock_mean': mean(x['air_primary_vehicles'] for x in ours),
                'train_stock_mean': mean(x['primary_vehicles_by_mode']['rail'] for x in ours),
                'airport_count_mean': mean(x['air_airports'] for x in ours),
                'airport_towns_mean': mean(x['airport_towns_opex_present'] for x in ours),
                'opcodes_complete_all': all(x.get('observed_opcode_complete_cpu') for x in ours),
                'pairs': {str(s): {'opex': x['profit_year'], 'aaa': y['profit_year']}
                          for s, x, y in zip(SEEDS20, ours, theirs)}}
    variant, off = summarize(arms[policy]), summarize(arms['reference'])
    return {**identity, **variant, 'health': '40/40 complete',
            'policy_id': policy, 'campaign': campaign,
            'own_off': {k: off[k] for k in ('ratio_pct', 'opex_profit_mean',
                                          'aaa_profit_mean')},
            'source_provenance': '40x5 frozen SHA matches 20x10 and all annual checkpoints',
            'limitations': 'Observed opcode counters are partial; 1979 profit alone determines economic rank'}, None


def analyze(repo, frozen):
    candidates, pending = [], []
    for row in frozen['locked_40x5_ranking']:
        complete, error = analyze_one(repo, row)
        if error:
            pending.append(error)
        else:
            candidates.append(complete)
    candidates.sort(key=lambda r: r['ratio_pct'], reverse=True)
    return {'economic_criterion': frozen['criterion_10y'],
            'same_seed_set': frozen['seeds20'],
            'ranked_healthy_20x10': candidates,
            'not_yet_qualified': pending,
            'winner': candidates[0] if len(candidates) == 3 else None,
            'default_authorized': True,
            'default_integrated': False,
            'note': 'Winner only when ALL three complete healthy 20x10; never promote partial data'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository', type=Path, required=True)
    ap.add_argument('--ranking', type=Path, required=True)
    ap.add_argument('--frozen', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--freeze', action='store_true')
    args = ap.parse_args()
    if args.freeze:
        if args.frozen.exists():
            raise FileExistsError('Top three frozen already; never silently reselect')
        raw = json.loads(args.ranking.read_text('utf-8'))
        data = freeze(raw)
        args.frozen.write_text(json.dumps(data, indent=2) + '\n', 'utf-8')
        print('FROZEN_TOP3', [(r['suite'], r['name'], r['ratio_40x5_pct'])
                              for r in data['locked_40x5_ranking']])
        return
    data = json.loads(args.frozen.read_text('utf-8'))
    result = analyze(args.repository, data)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    for row in result['ranked_healthy_20x10']:
        print('QUALIFIED', row['suite'], row['name'], f"{row['ratio_pct']:.6f}%",
              row['opex_profit_mean'], row['aaa_profit_mean'])
    print('PENDING', result['not_yet_qualified'])
    if result['winner']:
        print('WINNER_DEFAULT', result['winner']['suite'], result['winner']['name'])


if __name__ == '__main__':
    main()
