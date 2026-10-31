"""Rank independent finished V161 interaction duels, without economic vetoes.

Each ratio is derived from Opex and AAA profits in THE SAME variant duel.
Partially written or unhealthy runs never enter the confirmed rankings.
Historical OFF mismatch is reported, not conflated with source identity.
"""
import argparse
import hashlib
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
    'rail1970': ('estim31_v161_rail1970_20261030', 'estim31r1970'),
    'capcombo': ('estim31_v161_capcombo20261030', 'estim31capco'),
}


def check_health(report, count):
    games = report.get('games', [])
    return (not report.get('failed_runs') and len(games) == count
            and all(g.get('game_ok') and g.get('game_status') == 'complete'
                    for g in games))


def check_qualification(report, reference, variant, campaign, policy, manifest_path):
    """Verify exact seed/policy/source pairs, rather than merely game counts."""
    if not check_health(report, 80):
        return 'unhealthy or incomplete final report'
    if (report.get('campaign_id') != campaign or report.get('policy_id') != 'reference'
            or report.get('years') != 5 or report.get('start_year') != 1970
            or report.get('repeats') != 1 or report.get('map_size') != 8
            or report.get('expected_last_checkpoint') != '1974-12-01'
            or set(report.get('seeds', [])) != set(SEEDS40)
            or len(report.get('seeds', [])) != 40):
        return 'campaign, horizon or seed manifest mismatch'
    policies = report.get('policies', [])
    if len(policies) != 2 or {p.get('id') for p in policies} != {'reference', policy}:
        return 'reference/variant policy manifest mismatch'
    try:
        explicit = {p['id']: dict(p['explicit_settings']) for p in policies}
    except (KeyError, TypeError, ValueError):
        return 'invalid policy settings manifest'
    if (explicit['reference'] != {'probes': 2}
            or explicit[policy].get('estim_unifie') != 31
            or explicit[policy].get('probes') != 2):
        return 'reference OFF or ESTIM variant settings mismatch'
    source_sha = report.get('source_bundle_sha256')
    if not isinstance(source_sha, str) or len(source_sha) != 64:
        return 'missing source bundle SHA256'
    if (not manifest_path.is_file()
            or hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            != report.get('manifest_sha256')):
        return 'missing or altered run manifest'
    game_keys = set()
    for game in report['games']:
        key = (game.get('seed'), game.get('policy_id'), game.get('repeat'))
        if (key in game_keys or game.get('campaign_id') != campaign
                or game.get('source_bundle_sha256') != source_sha
                or game.get('expected_last_checkpoint') != '1974-12-01'):
            return 'duplicate game or game provenance mismatch'
        game_keys.add(key)
        companies = game.get('companies', {})
        if any(not companies.get(company, {}).get('horizon_complete')
               or companies[company].get('status') != 'complete'
               or not companies[company].get('run_ok')
               for company in ('OpexAI', 'AAAHogEx')):
            return 'incomplete company or invalid run'
    expected_games = {(seed, p, 0) for seed in SEEDS40
                      for p in ('reference', policy)}
    if game_keys != expected_games:
        return 'games do not cover identical 40 seeds in both policies'
    expected_checkpoints = {(seed, company, f'{year}-12-01')
                            for seed in SEEDS40
                            for company in ('OpexAI', 'AAAHogEx')
                            for year in range(1970, 1975)}
    for name, arm in (('reference', reference), (policy, variant)):
        if set(arm) != expected_checkpoints:
            return f'{name}: incomplete/misaligned 40-seed annual checkpoints'
        if any(row.get('campaign_id') != campaign
               or row.get('duel_policy_id') != name
               or row.get('source_bundle_sha256') != source_sha
               or list(row.get('run', [])) != [key[1], key[0], 0]
               for key, row in arm.items()):
            return f'{name}: mixed source/campaign/identity checkpoints'
    return None


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
        arms = parse(jsonl_path, prefix + '_' + name)
        reference, variant = arms['reference'], arms[prefix + '_' + name]
        problem = check_qualification(report, reference, variant, campaign,
                                      prefix + '_' + name,
                                      resultdir / (campaign + '.manifest.json'))
        if problem:
            pending.append([name, problem]); continue
        source_sha = report.get('source_bundle_sha256')
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
