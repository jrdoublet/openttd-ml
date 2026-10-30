"""40×5 ESTIM-31 rank: ratio of arithmetic means, no economic veto.

This reader keeps provenance, simulation health, descriptive bootstrap and
historical OFF drift separate. Observed opcodes are partial; asset stocks and
capital quotes are NOT cash acquisitions or expenditure ledgers.
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean

from sweeps.estim31_joint_newgrid_analyse_20261030 import SEEDS40

END = '1974-12-01'
DATES = {f'{y}-12-01' for y in range(1970, 1975)}
FIELDS = ('profit_year','company_value','money','air_primary_vehicles',
          'air_airports','observed_opcodes_total','air_engine_counts')


def parse(path, selected, seeds=SEEDS40):
    arms = {'reference':{}, selected:{}}
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            policy = row.get('duel_policy_id')
            if policy not in arms or row.get('date') not in DATES:
                continue
            company, seed, repeat = row['run']
            if repeat != 0 or seed not in seeds:
                continue
            key = (seed, company, row['date'])
            if key in arms[policy]:
                raise ValueError(f'duplicate checkpoint: {key} {policy}')
            arms[policy][key] = row
    return arms


def ratio(arm, seeds=SEEDS40):
    ours = sum(arm[(s,'OpexAI',END)]['profit_year'] for s in seeds)
    aaa = sum(arm[(s,'AAAHogEx',END)]['profit_year'] for s in seeds)
    if aaa <= 0:
        raise ValueError('non-positive AAA denominator')
    return 100.0 * ours / aaa


def ci95(arm, seeds=SEEDS40, samples=10000):
    rng = random.Random(20261030)
    vals = []
    for _ in range(samples):
        draw = [seeds[rng.randrange(len(seeds))] for _ in seeds]
        vals.append(ratio(arm, draw))
    vals.sort()
    return [vals[int((len(vals)-1)*.025)], vals[int((len(vals)-1)*.975)]]


def describe_arm(arm, seeds=SEEDS40):
    ours = [arm[(s,'OpexAI',END)] for s in seeds]
    aaa = [arm[(s,'AAAHogEx',END)] for s in seeds]
    engines = Counter()
    for row in ours:
        engines.update(row.get('air_engine_counts') or {})
    return dict(ratio_pct=ratio(arm,seeds), ratio_ci95=ci95(arm,seeds),
                opex_profit_mean=mean(r['profit_year'] for r in ours),
                aaa_profit_mean=mean(r['profit_year'] for r in aaa),
                paired_profit_difference_mean=mean(a['profit_year']-b['profit_year']
                                                   for a,b in zip(ours,aaa)),
                opex_cash_mean=mean(r['money'] for r in ours),
                aaa_cash_mean=mean(r['money'] for r in aaa),
                opex_loan_mean=mean(r['current_loan'] for r in ours),
                aaa_loan_mean=mean(r['current_loan'] for r in aaa),
                aircraft_stock_mean=mean(r['air_primary_vehicles'] for r in ours),
                train_stock_mean=mean(r['primary_vehicles_by_mode']['rail'] for r in ours),
                airport_count_mean=mean(r['air_airports'] for r in ours),
                airport_towns_mean=mean(r['airport_towns_opex_present'] for r in ours),
                observed_opcodes_mean=mean(r['observed_opcodes_total'] for r in ours),
                opcodes_complete_all=all(r.get('observed_opcode_complete_cpu') for r in ours),
                final_engine_stocks=dict(engines),
                confirmed_cash_spend_by_category=None,
                financing_note='Cash spends cannot be inferred from quotes, vehicle stocks, profit and loan.',
                pairs={str(s):{'opex':a['profit_year'],'aaa':b['profit_year']}
                       for s,a,b in zip(seeds,ours,aaa)})


def analyze(repo, suite='safe'):
    prefix,dirname = {'safe':('estim31safe','estim31_joint_safe20261030'),
                      'railnorm':('estim31rnsafe','estim31_railnorm_safe20261030'),
                      'motorjoint':('estim31motor','estim31_motor_joint20261030'),
                      'v161':('estim31v161','estim31_v161_safe20261030')}[suite]
    baseline = repo/'results/estim31_engine_dispatch_air15_root_20261029/results/estim31_engine_dispatch_air15_40x5_20261029.jsonl'
    old = parse(baseline,'eb3_air15_dispatch')['reference']
    if len(old) != len(SEEDS40)*10:
        raise ValueError('historical 40×5 reference incomplete')
    result = []; pending = []
    for dirpath in sorted((repo/'results'/dirname).iterdir()):
        if not dirpath.is_dir() or not (dirpath/'design.json').is_file():
            continue
        name = dirpath.name
        campaign = f'{prefix}_{name}_40x5_20261030'
        path = dirpath/'results'/f'{campaign}.jsonl'
        report = dirpath/'results'/f'{campaign}.json'
        if not (path.is_file() and report.is_file()):
            pending.append([name,'not completed']); continue
        summary = json.loads(report.read_text('utf-8'))
        if (summary.get('failed_runs') or len(summary.get('games',[])) != 80
                or any(not g.get('game_ok') or g.get('game_status') != 'complete'
                       for g in summary['games'])):
            pending.append([name,'failed/unhealthy']); continue
        arms = parse(path,prefix+'_'+name)
        ref, var = arms['reference'], arms[prefix+'_'+name]
        if len(ref) != 400 or len(var) != 400:
            pending.append([name,f'checkpoints {len(ref)}/{len(var)}']); continue
        sha = summary.get('source_bundle_sha256')
        if not sha or {r.get('source_bundle_sha256') for r in (*ref.values(),*var.values())} != {sha}:
            pending.append([name,'source checksum inconsistent']); continue
        mismatches = sum(old[key].get(field) != ref[key].get(field)
                         for key in old for field in FIELDS)
        result.append(dict(name=name, suite=suite, configuration=json.loads(
              (dirpath/'design.json').read_text('utf-8'))['configuration'],
              health='80/80 complete', source_bundle_sha256=sha,
              reference_off_ratio_pct=ratio(ref),
              historical_off_mismatches=mismatches,
              historical_off_comparisons=len(old)*len(FIELDS),
              **describe_arm(var)))
    result.sort(key=lambda r:r['ratio_pct'],reverse=True)
    return dict(suite=suite, complete=result, pending=pending,
                criterion='100 * mean_40(profit_year Opex) / mean_40(profit_year AAA)',
                sample='40 paired map seeds, year 1974-12-01, 1970-1974')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--suite',choices=('safe','railnorm','motorjoint','v161'),default='safe')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    results=analyze(args.repository.resolve(),args.suite)
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n','utf-8')
    for v in results['complete']:
        print('40x5',v['name'],f"ratio={v['ratio_pct']:.6f}",
              f"Opex={v['opex_profit_mean']:.0f}",f"AAA={v['aaa_profit_mean']:.0f}",
              'OFFdiff='+str(v['historical_off_mismatches']))
    print('PENDING',results['pending'])


if __name__=='__main__':
    main()
