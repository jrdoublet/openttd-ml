"""Final ranking exclusively for technically validated 40x5 ESTIM31 duels.

Uses the same duel's OpexAI and AAAHogEx mean profits at 1974-12-01.
Never excludes a valid result for Wilcoxon, bootstrap, company value, or a
minimum profit gain. Unhealthy 5x5/40x5 games and partial campaigns are not
qualified. The historical OFF and old-GE campaigns stay COMPARATORS.
"""
import argparse
import json
from pathlib import Path

from sweeps.estim31_v161_newrank_20261030 import analyze_40x5, SUITES

REPORT_WORKTREE = Path(__file__).resolve().parent.parent


def rank(repo):
    baseline = json.loads(
        (REPORT_WORKTREE / 'docs/estim31_v161_40x5_20261030.json').read_text('utf-8'))
    if len(baseline['complete']) != 1:
        raise ValueError('V161 qualified anchor must have exactly one finished 40x5 result')
    anchor = dict(baseline['complete'][0])
    if anchor.get('health') != '80/80 complete':
        raise ValueError('Anchor is not healthy')
    anchor['suite'] = 'v161'
    qualified = [anchor]
    pending = []
    for suite in SUITES:
        analysis = analyze_40x5(repo, suite)
        qualified.extend(analysis['complete'])
        pending.extend({'suite': suite, 'name': name, 'reason': reason}
                       for name, reason in analysis['pending'])
    for row in qualified:
        if row['opex_profit_mean'] <= 0 or row['aaa_profit_mean'] <= 0:
            raise ValueError('Non-positive profit mean invalid in ranking')
        expected = 100 * row['opex_profit_mean'] / row['aaa_profit_mean']
        if abs(expected - row['ratio_pct']) > 1e-8:
            raise ValueError('Ratio-of-means mismatch ' + row['name'])
        if row['health'] != '80/80 complete':
            raise ValueError('Unhealthy finalist')
    qualified.sort(key=lambda row: row['ratio_pct'], reverse=True)
    best = qualified[0]
    return {
        'criterion': ('100 × mean_40(OpexAI profit_year 1974-12-01) / '
                      'mean_40(AAAHogEx-115 profit_year 1974-12-01), '
                      'both recorded in the same experiment duel'),
        'ranked': qualified,
        'not_yet_qualified': pending,
        'best_name': best['name'],
        'best_ratio_pct': best['ratio_pct'],
        'economics_no_veto': ('No minimum gain, company-value guard, Wilcoxon '
                              'or CI95 veto for a complete healthy source-proven duel'),
        'comparator_only': [
            dict(name='historical_off_40x5', ratio_pct=95.1563459911,
                 opex_profit_mean=2856232.650, aaa_profit_mean=3001620.775,
                 reason='historical reference, sources/execution not the same as 2026-10-30 duel'),
            dict(name='old_ge_40x5_a200_r150', ratio_pct=92.7851,
                 reason='ESTIM C121_GE shortcut without exhaustive-engine proof'),
            dict(name='newgrid_a200_r075_40x5', ratio_pct=94.460621,
                 reason='1 of 80 games stagnation_suspect and historical C121_GE'),
        ],
        'limitations': ('Source/bundle provenance, 40 game pairs, time cutoff and '
                        'health checked by individual suite readers. '
                        'Inter-campaign OFF differences can arise from execution '
                        'non-repeatability; descriptive CI and company value are '
                        'reported but not economic exclusion criteria.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = rank(args.repository.resolve())
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8')
    for i, item in enumerate(report['ranked'], 1):
        print(f"{i}. {item['suite']}/{item['name']} {item['ratio_pct']:.6f}% "
              f"Opex={item['opex_profit_mean']:.2f} AAA={item['aaa_profit_mean']:.2f} "
              f"SHA={item['source_bundle_sha256'][:12]}")
    print('PENDING', report['not_yet_qualified'])


if __name__ == '__main__':
    main()
