"""Rank only completed ESTIM-31 new-grid duels using December 1974 profit_year.

40x5 is a separate qualification; 5x5 results are only an exposure screen.
An OFF mismatch denotes a technical reproducibility issue, not a value/p veto.
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean

SEEDS40 = (42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,
           12345,54321,65537,123456,424242,8675309,423960,613553,515222,
           781335,375172,999533,442018,746035,455216,230185,706990,
           983759,802204,232037,723002,313707,701256,292001,841478,59527)
DATE = '1974-12-01'
DATES = tuple(f'{y}-12-01' for y in range(1970,1975))
FIELDS = ('profit_year','company_value','money','air_primary_vehicles',
          'air_airports','observed_opcodes_total','air_engine_counts')


def snapshots(file, seeds, selected_policy):
    arms = {'reference':{}, selected_policy:{}}
    with file.open(encoding='utf8') as f:
        for line in f:
            r = json.loads(line)
            arm = r.get('duel_policy_id')
            if arm not in arms or r.get('date') not in DATES or r['run'][1] not in seeds:
                continue
            key = (r['date'],r['run'][1],r['run'][0])
            if key in arms[arm]:
                raise ValueError(f'Duplicate {file}: {arm} {key}')
            arms[arm][key] = r
    return arms


def ratio(arm,seeds):
    ours = sum(arm[(DATE,s,'OpexAI')]['profit_year'] for s in seeds)
    aaa = sum(arm[(DATE,s,'AAAHogEx')]['profit_year'] for s in seeds)
    return 100*ours/aaa


def uncertainty(arm, base, seeds):
    rng = random.Random(20261030)
    v=[];delta=[]
    for _ in range(10000):
        selection = [seeds[rng.randrange(len(seeds))] for _ in seeds]
        a=ratio(arm,selection)
        v.append(a)
        delta.append(a-ratio(base,selection))
    def interval(xs):
        xs.sort()
        return [round(xs[int(.025*(len(xs)-1))],3),
                round(xs[int(.975*(len(xs)-1))],3)]
    return interval(v),interval(delta)


def analyze(root,n,name,base_off,base_est,seeds):
    directory=root/'results/estim31_joint_newgrid20261030'/name
    if not (directory/'design.json').exists():return None,'missing bundle'
    campaign=f'grid31_{name}_{n}x5_20261030'
    report=directory/'results'/f'{campaign}.json'
    path=directory/'results'/f'{campaign}.jsonl'
    if not (report.exists() and path.exists()):return None,'running or not started'
    summary=json.loads(report.read_text('utf8'))
    if (summary.get('failed_runs') or len(summary.get('games',[]))!=2*n
        or any(not g.get('game_ok') or g.get('game_status')!='complete'
               for g in summary['games'])):
        return None,'incomplete/unhealthy games'
    policy='grid31_'+name
    arms=snapshots(path,seeds,policy)
    ref=arms['reference'];var=arms[policy]
    if len(ref)!=n*10 or len(var)!=n*10:
        return None,f'incomplete checkpoints {len(ref)}/{len(var)}'
    sha=summary.get('source_bundle_sha256')
    if not sha or {r.get('source_bundle_sha256') for r in list(ref.values())+
                           list(var.values())}!={sha}:
        return None,'inconsistent bundle hash'
    errors=Counter()
    examples=[]
    for key, b in base_off.items():
        for field in FIELDS:
            if b.get(field)!=ref[key].get(field):
                errors[(key[1],field)] += 1
                if len(examples)<6:examples.append([key,field,b.get(field),ref[key].get(field)])
    ours=[var[(DATE,s,'OpexAI')] for s in seeds]
    rival=[var[(DATE,s,'AAAHogEx')] for s in seeds]
    engines=Counter()
    for row in ours:engines.update(row.get('air_engine_counts') or {})
    ci,delta_ci=uncertainty(var,base_est,seeds)
    design=json.loads((directory/'design.json').read_text('utf8'))
    output={
        'name':name, 'configuration':design['configuration'],
        'levers':design['levers'],'num_seeds':n,
        'ratio_pct':ratio(var,seeds),
        'opex_profit_mean':mean(r['profit_year'] for r in ours),
        'aaa_profit_mean':mean(r['profit_year'] for r in rival),
        'delta_vs_est31_reference_ratio_points':ratio(var,seeds)-ratio(base_est,seeds),
        'delta_vs_est31_reference_ci95':delta_ci, 'ratio_ci95':ci,
        'off_mismatch_count':sum(errors.values()),
        'off_mismatch_seeds':dict(Counter({s:sum(v for (t,_),v in errors.items() if t==s)
                                           for s,_ in errors})),
        'off_mismatch_examples':examples,
        'off_ratio_pct':ratio(ref,seeds),
        'technically_neutral_off':not errors,
        'healthy_games':2*n,
        'source_bundle_sha256':sha,
        'opex_aircraft_mean':mean(r['air_primary_vehicles'] for r in ours),
        'opex_airports_mean':mean(r['air_airports'] for r in ours),
        'opex_train_mean':mean(r['primary_vehicles_by_mode']['rail'] for r in ours),
        'opex_cash_mean':mean(r['money'] for r in ours),
        'opex_opcodes_observed_mean':mean(r['observed_opcodes_total'] for r in ours),
        'opcode_complete_all':all(r.get('observed_opcode_complete_cpu') for r in ours),
        'opex_engines_total':dict(engines),
        'seed_profit_pairs':{str(s):{
           'opex':var[(DATE,s,'OpexAI')]['profit_year'],
           'aaa':var[(DATE,s,'AAAHogEx')]['profit_year']} for s in seeds},
    }
    return output,None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',required=True,type=Path)
    p.add_argument('--seeds',required=True,type=int,choices=(5,40))
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    root=args.repository.resolve()
    seeds=SEEDS40[:args.seeds]
    suffix=f'{args.seeds}x5'
    baseline=root/'results/estim31_engine_dispatch_air15_root_20261029/results'/f'estim31_engine_dispatch_air15_{suffix}_20261029.jsonl'
    if args.seeds==5:
        source_policy='eb3_air15_dispatch'
    else:
        source_policy='eb3_air15_dispatch'
    base=snapshots(baseline,seeds,source_policy)
    base_off,base_est=base['reference'],base[source_policy]
    assert len(base_off)==args.seeds*10 and len(base_est)==args.seeds*10
    folder=root/'results/estim31_joint_newgrid20261030'
    eligible=[];pending=[]
    for directory in sorted(folder.iterdir()):
        if not directory.is_dir():continue
        val,err=analyze(root,args.seeds,directory.name,base_off,base_est,seeds)
        if err:pending.append([directory.name,err])
        else:eligible.append(val)
    eligible.sort(key=lambda x:x['ratio_pct'],reverse=True)
    for x in eligible:
        print('RANK',x['name'],f"ratio={x['ratio_pct']:.4f}",
              f"Opex={x['opex_profit_mean']:.0f}",
              f"AAA={x['aaa_profit_mean']:.0f}",
              'OFFdiff',x['off_mismatch_count'],
              'delta_vs_initial',round(x['delta_vs_est31_reference_ratio_points'],4))
    print('COMPLETE',len(eligible),'PENDING',pending)
    report={'seeds':list(seeds),'benchmark':suffix,
            'reference_est31_ratio_pct':ratio(base_est,seeds),
            'reference_off_ratio_pct':ratio(base_off,seeds),
            'complete':eligible,'pending':pending}
    outfile=(args.output or (folder/f'ranking_{suffix}.json')).resolve()
    outfile.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print('RESULT',outfile)


if __name__=='__main__':main()
