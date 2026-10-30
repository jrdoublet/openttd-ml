"""Rank only finished ESTIM31 multi-lever discovery duels (December 1974).

Each scenario's variation is compared to AAAHogEx in its OWN duel. OFF
cross-bundle equality is diagnosed, not assumed. Does not promote 5×5 to 40×5.
"""
import argparse
import json
import random
from pathlib import Path
from statistics import mean
from collections import Counter

DATES = tuple(f'{y}-12-01' for y in range(1970,1975))
END = DATES[-1]
SEEDS = (42,100,7,999,2026)
FIELDS = ('profit_year','company_value','money','air_primary_vehicles',
          'air_airports','observed_opcodes_total','air_engine_counts')


def read(path, variant):
    out={'reference':{},variant:{}}
    for line in path.read_text('utf8').splitlines():
        r=json.loads(line)
        policy=r.get('duel_policy_id')
        if policy not in out or r.get('date') not in DATES:continue
        company,seed=r['run'][:2]
        if seed not in SEEDS:continue
        key=(r['date'],seed,company)
        if key in out[policy]:raise ValueError(f'duplicate {path}: {policy} {key}')
        out[policy][key]=r
    return out['reference'],out[variant]


def ratio(recs, chosen=SEEDS):
    op=sum(recs[(END,s,'OpexAI')]['profit_year'] for s in chosen)
    other=sum(recs[(END,s,'AAAHogEx')]['profit_year'] for s in chosen)
    return 100*op/other


def analyze(repo, directory='estim31_joint_next20261030', prefix='estim31next'):
    folder=repo/'results'/directory
    source=repo/'results/estim31_engine_dispatch_air15_root_20261029/results/estim31_engine_dispatch_air15_5x5_20261029.jsonl'
    old,baseline=read(source,'eb3_air15_dispatch')
    result=[];pending=[]
    for target in sorted(folder.iterdir()):
        if not target.is_dir():continue
        design=json.loads((target/'design.json').read_text('utf8'))
        name=target.name
        campaign=f'{prefix}_{name}_5x5_20261030'
        outfile=target/'results'/f'{campaign}.json'
        path=target/'results'/f'{campaign}.jsonl'
        if not outfile.exists() or not path.exists():
            pending.append(name);continue
        record=json.loads(outfile.read_text('utf8'))
        games=record.get('games',[])
        if record.get('failed_runs') or len(games)!=10 or any(
                not g.get('game_ok') or g.get('game_status')!='complete' for g in games):
            pending.append(name+': unhealthy');continue
        off,vari=read(path,prefix+'_'+name)
        if len(off)!=50 or len(vari)!=50:
            pending.append(name+f': incomplete {len(off)} {len(vari)}');continue
        source_sha=record.get('source_bundle_sha256')
        if not source_sha or {r.get('source_bundle_sha256') for r in (*off.values(),*vari.values())}!={source_sha}:
            pending.append(name+': source mismatch');continue
        diff=[(key,field) for key in old for field in FIELDS
              if old[key].get(field)!=off[key].get(field)]
        op=mean(vari[(END,s,'OpexAI')]['profit_year'] for s in SEEDS)
        aa=mean(vari[(END,s,'AAAHogEx')]['profit_year'] for s in SEEDS)
        rng=random.Random(20261030)
        ci=[]; ratio_ci=[]
        for _ in range(5000):
            sample=[SEEDS[rng.randrange(len(SEEDS))] for _ in SEEDS]
            v=ratio(vari,sample)
            ratio_ci.append(v)
            ci.append(v-ratio(baseline,sample))
        ci.sort()
        ratio_ci.sort()
        engines=Counter()
        for s in SEEDS:engines.update(vari[(END,s,'OpexAI')].get('air_engine_counts') or {})
        result.append(dict(name=name,configuration=design['configuration'],
              ratio_pct=ratio(vari),opex_profit_mean=op,aaa_profit_mean=aa,
              baseline_ratio_5x5=ratio(baseline),delta_ratio_pts=ratio(vari)-ratio(baseline),
              delta_ratio_ci95=[round(ci[124],3),round(ci[4874],3)],
              ratio_ci95=[round(ratio_ci[124],3),round(ratio_ci[4874],3)],
              paired_profit_delta_mean=op-aa,
              off_mismatches=len(diff),off_mismatch_by_seed=dict(Counter(k[1] for k,_ in diff)),
              off_comparisons=len(old)*len(FIELDS),technically_neutral_off=(not diff),
              off_ratio_pct=ratio(off),
              cash_mean=mean(vari[(END,s,'OpexAI')]['money'] for s in SEEDS),
              aaa_cash_mean=mean(vari[(END,s,'AAAHogEx')]['money'] for s in SEEDS),
              loan_mean=mean(vari[(END,s,'OpexAI')]['current_loan'] for s in SEEDS),
              air_mean=mean(vari[(END,s,'OpexAI')]['air_primary_vehicles'] for s in SEEDS),
              rail_mean=mean(vari[(END,s,'OpexAI')]['primary_vehicles_by_mode']['rail'] for s in SEEDS),
              airports_mean=mean(vari[(END,s,'OpexAI')]['air_airports'] for s in SEEDS),
              airport_towns_mean=mean(vari[(END,s,'OpexAI')]['airport_towns_opex_present'] for s in SEEDS),
              opcodes_observed_mean=mean(vari[(END,s,'OpexAI')]['observed_opcodes_total'] for s in SEEDS),
              opcodes_complete=all(vari[(END,s,'OpexAI')]['observed_opcode_complete_cpu'] for s in SEEDS),
              pairs={str(s):dict(opex=vari[(END,s,'OpexAI')]['profit_year'],
                       aaa=vari[(END,s,'AAAHogEx')]['profit_year']) for s in SEEDS},
              air_engines=dict(engines),source_bundle_sha256=source_sha))
    result.sort(key=lambda x:x['ratio_pct'],reverse=True)
    return result,pending


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--directory',default='estim31_joint_next20261030')
    p.add_argument('--prefix',default='estim31next')
    a=p.parse_args()
    ranking,pending=analyze(a.repository.resolve(), a.directory, a.prefix)
    for x in ranking:
        print('SCENARIO',x['name'],f"ratio={x['ratio_pct']:.4f}",
              f"Opex={x['opex_profit_mean']:.0f}",f"AAA={x['aaa_profit_mean']:.0f}",
              'OFF_mismatch=',x['off_mismatches'])
    print('PENDING',pending)
    a.output.write_text(json.dumps({'complete':ranking,'pending':pending},
                                   indent=2,ensure_ascii=False)+'\n','utf8')


if __name__=='__main__':main()
