"""Review AC04-A / AC06 VM opcode v1 vs optimized v2, paired seeds/windows.

Usage: python sweeps/analyse_ac_opcode_v2.py <master-root> <case>
The two bundles are deliberately distinct; each comparison is within its
own frozen OFF/ON pair, never a cross-bundle contrast of raw totals.
"""
import json
from pathlib import Path
import random
import statistics
import sys


def bootstrap_ci(values, n=20000):
    rng = random.Random(0)
    m = len(values)
    draws = sorted(sum(values[rng.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return [draws[int((n - 1) * 0.025)], draws[int((n - 1) * 0.975)]]


def describe(report, years):
    values = [sum(report['paired'][str(s)][y]['loop_executed_ops_delta'] for y in years)
              for s in report['seeds']]
    refs = [sum(report['paired'][str(s)][y]['loop_executed_ops_ref'] for y in years)
            for s in report['seeds']]
    return {'n': len(values), 'years': list(years),
            'mean_delta': statistics.mean(values),
            'median_delta': statistics.median(values),
            'ratio_of_means': 1+statistics.mean(values)/statistics.mean(refs),
            'ci95_bootstrap': bootstrap_ci(values),
            'positive': sum(v > 0 for v in values),
            'negative': sum(v < 0 for v in values),
            'equal': sum(v == 0 for v in values)}


def analyse(root, case):
    stage = root / 'results/ac_fixes_worktree_20261011/results'
    opt = root / 'results/ac_opcode_opt_worktree_20261011/results'
    base = json.loads((stage / f'{case}_opcode_loop_10x4_20261011_phase_summary.json').read_text(encoding='utf8'))
    v2 = json.loads((opt / f'{case}_optv2_opcode_loop_10x4_20261011_phase_summary.json').read_text(encoding='utf8'))
    assert base['valid'] and v2['valid'] and base['source_frozen'] and v2['source_frozen']
    assert base['seeds'] == v2['seeds'] and len(base['seeds']) == 10
    assert base['observed_complete_years'] == v2['observed_complete_years'] == ['1970','1971','1972']
    windows = [('1970',), ('1970','1971'), ('1970','1971','1972')]
    return {'case': case, 'v1_source': base['source'], 'v2_source': v2['source'],
            'same_seeds': True, 'years': { '+'.join(years): {
                'v1': describe(base, years), 'v2': describe(v2, years)}
                for years in windows},
            'reference_equal_per_seed_year': sum(
                all(base['paired'][str(s)][y]['loop_executed_ops_ref'] ==
                    v2['paired'][str(s)][y]['loop_executed_ops_ref']
                    for y in ('1970','1971','1972'))
                for s in base['seeds'])}


if __name__ == '__main__':
    root = Path(sys.argv[1])
    case = sys.argv[2]
    report = analyse(root, case)
    output = root / 'results/ac_opcode_opt_worktree_20261011/results' / f'{case}_optv2_vs_v1_window_analysis.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False))
