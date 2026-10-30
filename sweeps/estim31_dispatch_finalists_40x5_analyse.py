"""Rank completed 40×5 ESTIM-31 joint bundles on *relative* profit only.

Valid source/physics/off-path parity is a prerequisite to using a number.
Neither company value nor Wilcoxon p is an economic rejection criterion.
Paired bootstrap resamples whole maps, keeping policy/company correlations.
"""
import argparse
import json
import random
from pathlib import Path
from statistics import mean
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
SEEDS=(42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,
       12345,54321,65537,123456,424242,8675309,423960,613553,515222,
       781335,375172,999533,442018,746035,455216,230185,706990,
       983759,802204,232037,723002,313707,701256,292001,841478,59527)
DATES=tuple(f'{y}-12-01' for y in range(1970,1975))
DATE=DATES[-1]
CHECKS=('profit_year','company_value','money','air_primary_vehicles',
        'air_airports','observed_opcodes_total','air_engine_counts')


def read(file,policy):
    ref={};variant={}
    for line in file.read_text('utf8').splitlines():
        r=json.loads(line)
        if r.get('date') not in DATES or r['run'][1] not in SEEDS:continue
        p=r.get('duel_policy_id')
        if p not in ('reference',policy):continue
        group=ref if p=='reference' else variant
        key=(r['date'],r['run'][1],r['run'][0])
        if key in group:raise ValueError((file,'duplicate',p,key))
        group[key]=r
    return ref,variant


def ratio(records,seeds):
    num=sum(records[(DATE,s,'OpexAI')]['profit_year'] for s in seeds)
    den=sum(records[(DATE,s,'AAAHogEx')]['profit_year'] for s in seeds)
    return 100*num/den if den else None


def bs_ci(ref,candidate):
    rng=random.Random(20261029)
    vals=[];deltas=[]
    for _ in range(20000):
        seeds=[SEEDS[rng.randrange(len(SEEDS))] for _ in SEEDS]
        v=ratio(candidate,seeds); r=ratio(ref,seeds)
        vals.append(v);deltas.append(v-r)
    def ci(xs):
        a=sorted(xs)
        return [round(a[int(.025*(len(a)-1))],3),round(a[int(.975*(len(a)-1))],3)]
    return ci(vals),ci(deltas)


def metrics(records):
    rows=[records[(DATE,s,'OpexAI')] for s in SEEDS]
    rivals=[records[(DATE,s,'AAAHogEx')] for s in SEEDS]
    out={'opex_profit_mean':mean(r['profit_year'] for r in rows),
         'aaa_profit_mean':mean(r['profit_year'] for r in rivals),
         'ratio_pct':ratio(records,SEEDS)}
    for field in ('money','company_value','air_primary_vehicles','air_airports',
                  'observed_opcodes_total','airport_towns_opex_present',
                  'airport_towns_aaahogex_present','airport_towns_aaahogex_2_opex_0',
                  'income_last_year','expenses_last_year',
                  'project_builds_sign_total','town_growth_builds_sign_total'):
        vs=[r.get(field) for r in rows]
        if all(isinstance(v,(float,int)) for v in vs):out['opex_'+field+'_mean']=mean(vs)
    out['opex_rail_vehicles_mean']=mean(r['primary_vehicles_by_mode']['rail'] for r in rows)
    out['observed_opcodes_complete_cpu_all']=all(
        r.get('observed_opcode_complete_cpu',False) for r in rows)
    engines=Counter()
    for row in rows:engines.update(row.get('air_engine_counts') or {})
    out['opex_engine_counts_40_maps']=dict(engines)
    out['seed_profits']={str(s):{'opex':records[(DATE,s,'OpexAI')]['profit_year'],
                                'aaa':records[(DATE,s,'AAAHogEx')]['profit_year']}
                         for s in SEEDS}
    history=[]
    for year_end in DATES:
        yr=int(year_end[:4])
        ours=[records[(year_end,s,'OpexAI')] for s in SEEDS]
        other=[records[(year_end,s,'AAAHogEx')] for s in SEEDS]
        state={'date':year_end,
               'opex_profit_year':mean(x['profit_year'] for x in ours),
               'aaahogex_profit_year':mean(x['profit_year'] for x in other),
               'opex_income_last_year':mean(x['income_last_year'] for x in ours),
               'opex_expenses_last_year':mean(x['expenses_last_year'] for x in ours),
               'opex_cash':mean(x['money'] for x in ours),
               'opex_loan':mean(x['current_loan'] for x in ours),
               'opex_aircraft':mean(x['air_primary_vehicles'] for x in ours),
               'opex_airports':mean(x['air_airports'] for x in ours),
               'opex_trains':mean(x['primary_vehicles_by_mode']['rail'] for x in ours),
               'opex_project_build_signs_total':sum(x.get('project_builds_sign_total',0) for x in ours),
               'opex_town_growth_build_signs_total':sum(x.get('town_growth_builds_sign_total',0) for x in ours)}
        if yr>1970:
            before=f'{yr-1}-12-01'
            residue=[]
            for s in SEEDS:
                p=records[(year_end,s,'OpexAI')]
                q=records[(before,s,'OpexAI')]
                residue.append(p['profit_year'] + p['current_loan']-q['current_loan']
                               - (p['money']-q['money']))
            state['net_nonoperating_residual_not_attributed']=mean(residue)
        history.append(state)
    out['annual_history']=history
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-root',type=Path,default=ROOT,
                        help='Repository root hosting frozen results/ bundles')
    parser.add_argument('--output',type=Path,
                        help='Output ranking JSON (defaults to results/estim31_joint_dispatch20261029)')
    parser.add_argument('--scenarios',nargs='+',
                        default=('a150_r100_w05','a100_r100_w15_flat',
                                 'a150_r100_w05_flat_load25'),
                        help='Only qualified campaigns explicitly launched for 40×5')
    args=parser.parse_args()
    root=args.results_root.resolve()
    folder_path=root/'results/estim31_joint_dispatch20261029'
    base_file=(root/'results/estim31_engine_dispatch_air15_root_20261029/results/'
               'estim31_engine_dispatch_air15_40x5_20261029.jsonl')
    baseline,base_dispatch=read(base_file,'eb3_air15_dispatch')
    assert len(baseline)==5*40*2
    complete=[];pending=[];variants={'initial_A150_R100_w15_sloped':base_dispatch,
                                    'OFF_historical':baseline}
    for name in args.scenarios:
        folder=folder_path/name
        if not (folder/'design.json').is_file():
            pending.append(f'{name}: no design.json')
            continue
        campaign=f'dispatch31_{name}_40x5_20261029'
        file=folder/'results'/f'{campaign}.jsonl'
        summary=folder/'results'/f'{campaign}.json'
        # Never interpret an active/partially written JSONL as a completed duel.
        if not summary.exists() or not file.exists():pending.append(name);continue
        campaign_report=json.loads(summary.read_text('utf8'))
        finished_games=campaign_report.get('games',[])
        if (campaign_report.get('failed_runs') or len(finished_games)!=80
                or any(not g.get('game_ok') or g.get('game_status')!='complete'
                       for g in finished_games)):
            pending.append(f'{name}: unhealthy or incomplete games in final JSON')
            continue
        reference,variant=read(file,'dispatch31_'+name)
        if len(reference)!=400 or len(variant)!=400:
            pending.append(f'{name}: {len(reference)} OFF + {len(variant)} variant snapshots')
            continue
        expected_sha=campaign_report.get('source_bundle_sha256')
        seen_sha={r.get('source_bundle_sha256')
                  for r in list(reference.values())+list(variant.values())}
        if not expected_sha or seen_sha!={expected_sha}:
            pending.append(f'{name}: inconsistent frozen source SHA256')
            continue
        diffs=[]
        for key, b in baseline.items():
            t=reference[key]
            for field in CHECKS:
                if b.get(field)!=t.get(field):diffs.append((key,field,b.get(field),t.get(field)))
        c=metrics(variant)
        ci,delta_ci=bs_ci(baseline,variant)
        offratio=ratio(reference,SEEDS)
        diffs_profit=[variant[(DATE,s,'OpexAI')]['profit_year']
                    -baseline[(DATE,s,'OpexAI')]['profit_year'] for s in SEEDS]
        c.update(name=name,off_parity_mismatches=len(diffs),off_mismatch_examples=diffs[:6],
                 off_checks=40*5*2*len(CHECKS),off_ratio_pct=offratio,
                 completed_games=len(finished_games),healthy_paired_seeds=len(SEEDS),
                 source_bundle_sha256=expected_sha,
                 technically_neutral_off=(len(diffs)==0),
                 ratio_ci95=ci,delta_vs_OFF_ratio_points=c['ratio_pct']-ratio(baseline,SEEDS),
                 delta_ratio_ci95=delta_ci,
                 opex_profit_delta_vs_OFF_mean=mean(diffs_profit),
                 opex_wins_vs_OFF=sum(x>0 for x in diffs_profit),
                 source_bundle=str(folder),campaign=campaign)
        complete.append(c)
        variants[name]=variant
    complete.sort(key=lambda d:(d['technically_neutral_off'],d['ratio_pct']),reverse=True)
    for row in complete:
        print('QUALIFIED' if row['technically_neutral_off'] else 'NON_NEUTRAL',row['name'],
              'ratio',round(row['ratio_pct'],4),'Opex',round(row['opex_profit_mean']),
              'AAA',round(row['aaa_profit_mean']),'deltaOFF',round(row['delta_vs_OFF_ratio_points'],3),
              'CI95',row['ratio_ci95'],'OFF_mismatch',row['off_parity_mismatches'])
    print('PENDING',pending)
    # Compare each accepted final profile against ALL other complete accepted
    # profiles, keeping the same shared map draws for opponent and Opex alike.
    eligible=['OFF_historical','initial_A150_R100_w15_sloped'] + [
        row['name'] for row in complete if row['technically_neutral_off']]
    comparisons=[]
    rng=random.Random(20261030)
    for i in range(len(eligible)):
        for j in range(i+1,len(eligible)):
            left,right=eligible[i],eligible[j]
            observed=ratio(variants[right],SEEDS)-ratio(variants[left],SEEDS)
            simulated=[]
            for _ in range(10000):
                chosen=[SEEDS[rng.randrange(len(SEEDS))] for _ in SEEDS]
                simulated.append(ratio(variants[right],chosen)-ratio(variants[left],chosen))
            simulated.sort()
            ci=[round(simulated[int(.025*(len(simulated)-1))],3),
                round(simulated[int(.975*(len(simulated)-1))],3)]
            comparisons.append({'left':left,'right':right,
                                'right_minus_left_ratio_points':round(observed,4),
                                'CI95_paired_bootstrap':ci})
            print('PAIRWISE',right,'minus',left,'delta',round(observed,4),'CI95',ci)
    # Complete the descriptive comparison matrix. Nonmatching OFF controls
    # prevent technical promotion, but not a transparent economic diagnosis.
    all_names=['OFF_historical','initial_A150_R100_w15_sloped'] + [
        row['name'] for row in complete]
    exploratory=[]
    for i in range(len(all_names)):
        for j in range(i+1,len(all_names)):
            left,right=all_names[i],all_names[j]
            rng=random.Random(20261030+100*i+j)
            vals=[]
            for _ in range(10000):
                chosen=[SEEDS[rng.randrange(len(SEEDS))] for _ in SEEDS]
                vals.append(ratio(variants[right],chosen)-ratio(variants[left],chosen))
            vals.sort()
            exploratory.append({
                'left':left,'right':right,
                'right_minus_left_ratio_points':round(ratio(variants[right],SEEDS)
                                                  -ratio(variants[left],SEEDS),4),
                'CI95_paired_bootstrap':[round(vals[int(.025*(len(vals)-1))],3),
                                         round(vals[int(.975*(len(vals)-1))],3)],
                'descriptive_only': (left not in eligible or right not in eligible),
            })
    off_metrics=metrics(baseline)
    initial_metrics=metrics(base_dispatch)
    initial_ci,initial_delta_ci=bs_ci(baseline,base_dispatch)
    initial_metrics['ratio_ci95']=initial_ci
    initial_metrics['delta_vs_OFF_ratio_points']=initial_metrics['ratio_pct']-off_metrics['ratio_pct']
    initial_metrics['delta_ratio_ci95']=initial_delta_ci
    out=args.output.resolve() if args.output else folder_path/'ranking_40x5.json'
    out.write_text(json.dumps({'off_historical':off_metrics,
                               'initial_ESTIM31_A150_R100_w15_sloped':initial_metrics,
                               'complete':complete,'pending':pending,
                               'paired_comparisons':comparisons,
                               'exploratory_pairwise_comparisons':exploratory},
                   indent=2,ensure_ascii=False)+'\n','utf8')
    print('REPORT',out)

if __name__=='__main__':main()
