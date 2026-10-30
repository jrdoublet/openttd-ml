"""Rank independent finished V161 interaction duels, without economic vetoes.

Each ratio is derived from Opex and AAA profits in THE SAME variant duel.
Partially written or unhealthy runs never enter the confirmed rankings.
Historical OFF mismatch is reported, not conflated with source identity.
"""
import argparse
import json
from pathlib import Path

from sweeps.estim31_joint_next_analyse import analyze as analyze_5x5
from sweeps.estim31_joint_safe_40x5_analyse_20261030 import (
    SEEDS40, FIELDS, describe_arm, parse, ratio)

SUITES = {
    'v161cap': ('estim31_v161_motorcap20261030', 'estim31vcap'),
    'v161policy': ('estim31_v161_policy20261030', 'estim31vp'),
    'noupper': ('estim31_no_upper20261030', 'estim31nohi'),
    'v161coeff': ('estim31_v161_coeff20261030', 'estim31vcoef'),
}


def check_health(report, count):
    games = report.get('games', [])
    return (not report.get('failed_runs') and len(games) == count
            and all(g.get('game_ok') and g.get('game_status') == 'complete'
                    for g in games))


def analyze_40x5(repo, suite):
    folder, prefix = SUITES[suite]
    root = repo / 'results' / folder
    old_path = (repo / 'results/estim31_engine_dispatch_air15_root_20261029/'
                'results/estim31_engine_dispatch_air15_40x5_20261029.jsonl')
    old = parse(old_path, 'eb3_air15_dispatch')['reference']
    if len(old) != 400:
        raise ValueError('Baseline 40x5 missing annual paired checkpoints')
    complete, pending = [], []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or not (directory / 'design.json').exists():
            continue
        name = directory.name
        campaign = f'{prefix}_{name}_40x5_20261030'
        resultdir = directory / 'results'
        json_path = resultdir / (campaign + '.json')
        jsonl_path = resultdir / (campaign + '.jsonl')
        if not json_path.is_file() or not jsonl_path.is_file():
            pending.append([name, 'result incomplete']); continue
        report = json.loads(json_path.read_text('utf-8'))
        if not check_health(report, 80):
            pending.append([name, 'unhealthy; not ranked']); continue
        arms = parse(jsonl_path, prefix + '_' + name)
        reference, variant = arms['reference'], arms[prefix + '_' + name]
        if len(reference) != 400 or len(variant) != 400:
            pending.append([name, f'checkpoints {len(reference)}/{len(variant)}']); continue
        source_sha = report.get('source_bundle_sha256')
        if (not source_sha
                or {r.get('source_bundle_sha256') for r in (*reference.values(), *variant.values())}
                != {source_sha}):
            pending.append([name, 'source mismatch']); continue
        mismatches = sum(reference[key].get(field) != old[key].get(field)
                         for key in old for field in FIELDS)
        details = describe_arm(variant)
        details.update(name=name, suite=suite, health='80/80 complete',
                       configuration=json.loads((directory / 'design.json').read_text('utf-8'))['configuration'],
                       source_bundle_sha256=source_sha,
                       own_reference_off_ratio_pct=ratio(reference),
                       historical_off_mismatches=mismatches,
                       historical_off_comparisons=len(old) * len(FIELDS))
        complete.append(details)
    complete.sort(key=lambda row: row['ratio_pct'], reverse=True)
    return {'suite': suite, 'complete': complete, 'pending': pending,
            'criterion': '100 x sum_40(variant Opex profit_year) / sum_40(variant AAA profit_year)',
            'ranking_cutoff': '1974-12-01', 'seeds': len(SEEDS40)}


def analyze_all(repo):
    result = {}
    for suite, (directory, prefix) in SUITES.items():
        short, missing = analyze_5x5(repo, directory, prefix)
        result[suite] = {'screen_5x5': {'complete': short, 'pending': missing},
                         'qualified_40x5': analyze_40x5(repo, suite)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze_all(args.repository.resolve())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    for suite in result:
        for scope, detail in result[suite].items():
            for row in detail['complete']:
                print(suite, scope, row['name'], f"{row['ratio_pct']:.5f}%",
                      f"Opex={row['opex_profit_mean']:.0f}",
                      f"AAA={row['aaa_profit_mean']:.0f}")
            print('PENDING', suite, scope, detail['pending'])


if __name__ == '__main__':
    main()
