"""Paired annual LOOP_OPS top-level windows; excludes nested budgets.

The measured windows include command wait/yield as 10k/tick, so they are
not per-instruction VM opcodes. Each arm is a separate shared-map duel.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import re
import statistics


LINE = re.compile(r'\[script:\d+\] \[0\] \[I\] LOOP_OPS y=(\d+) post=([^ ]+) n=(\d+) ops=(\d+) tk=(\d+)')
TOP = {'events','save_projection','station_flux','c117_sample','c117_skip',
       'orchestrator','catalog_continuation','catalog_continuation_check',
       'rail_throughput','c67_hook'}


def parse(path):
    years = defaultdict(dict)
    for row in path.read_text(encoding='utf8',errors='replace').splitlines():
        m = LINE.search(row)
        if not m:
            continue
        year, post, n, ops, ticks = m.groups()
        year = int(year)
        if post in years[year]:
            raise ValueError(f'duplicate {path} {year}/{post}')
        years[year][post] = {'n': int(n), 'ops':int(ops), 'tk':int(ticks)}
    output = {}
    for year, posts in years.items():
        tick_count = posts.get('_year',{}).get('tk')
        total = sum(posts[p]['ops'] for p in TOP if p in posts)
        if tick_count is None:
            raise ValueError(f'missing closing tick {path} {year}')
        if 'sleep_left' not in posts:
            raise ValueError(f'missing sleep_left {path} {year}')
        output[year] = {'ticks':tick_count, 'budget': tick_count*10000,
                        'occupied_top':total, 'sleep_left':posts['sleep_left']['ops'],
                        'remaining_gap':tick_count*10000-total-posts['sleep_left']['ops'],
                        'by_post':{p:posts[p]['ops'] for p in TOP if p in posts}}
    return output


def percentile(values, proportion):
    v=sorted(values)
    if not v:
        return None
    pos=(len(v)-1)*proportion
    a=int(pos)
    return v[a] + (v[min(a+1,len(v)-1)]-v[a])*(pos-a)


def analyze(engine, seeds, years):
    records={}
    for seed in seeds:
        left=parse(engine/f'reference_seed{seed}_r0.log')
        right=parse(engine/f'p0_topk_binary_seed{seed}_r0.log')
        required=set(years)
        if not required.issubset(left) or not required.issubset(right):
            raise ValueError(f'seed={seed}: missing annual closure ref={sorted(left)} variant={sorted(right)}')
        records[str(seed)]={str(y):{
            'reference':left[y], 'variant':right[y],
            'delta_occupied':right[y]['occupied_top']-left[y]['occupied_top'],
            'delta_budget':right[y]['budget']-left[y]['budget'],
            'delta_sleep_left':right[y]['sleep_left']-left[y]['sleep_left']}
            for y in years}
    paired=[sum(x['delta_occupied'] for x in records[str(seed)].values()) for seed in seeds]
    rng=random.Random(0)
    reps=[statistics.mean(rng.choices(paired,k=len(paired))) for _ in range(20000)]
    return {'seeds':seeds,'years':list(years),'by_seed':records,
            'paired_delta_occupied_by_seed':dict(zip(map(str,seeds),paired)),
            'mean_delta_occupied':statistics.mean(paired),
            'median_delta_occupied':statistics.median(paired),
            'wins_lower_occupied':sum(x<0 for x in paired),
            'losses_higher_occupied':sum(x>0 for x in paired),
            'equal_occupied':sum(x==0 for x in paired),
            'ci95_bootstrap_mean_delta':[round(percentile(reps,0.025),2),round(percentile(reps,0.975),2)],
            'mean_reference_occupied':statistics.mean(sum(records[str(s)][str(y)]['reference']['occupied_top'] for y in years) for s in seeds),
            'notes':['Only top-level LOOP_OPS categories are added. Never add sleep_left, tg_*, C39 or SPAN.',
                     'Occupied budget tick-windows include command waits and yields; not exclusive VM CPU instructions.',
                     'The 1979 closing report requires simulating a further year; these annual windows cover 1970-1978 in a 10-year run.',
                     'A/B trajectories may diverge so global occupied reductions can reflect less economically useful work.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('engine_logs',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seeds',nargs='+',type=int,default=[42,100,7,999,2026,1,17,73,314,512,
                                                        1024,1337,4096,8191,12345,54321,65537,123456,424242,8675309])
    p.add_argument('--years',nargs='+',type=int,default=list(range(1970,1979)))
    a=p.parse_args()
    d=analyze(a.engine_logs,a.seeds,a.years)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('mean delta',d['mean_delta_occupied'],'IC95',d['ci95_bootstrap_mean_delta'],
          'wins/losses',d['wins_lower_occupied'],d['losses_higher_occupied'])
    print('seed deltas',d['paired_delta_occupied_by_seed'])


if __name__=='__main__':
    main()
