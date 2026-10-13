#!/usr/bin/env python3
"""Read C66 tail shadow A/B engine logs, without summing overlapping counters.

TAIL_SHADOW samples are observational upper bounds, not recovered opcodes.
LOOP_OPS post=tail_shadow is the hook's inclusive metered cost, including
tick crossings. Between arms, trajectory may diverge: do not read changes in
sleep_left as savings or gains attributable to the hook.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics

from analyse_opcode_early4 import LINE, fields, YEARS


def read_log(path):
    loop = defaultdict(dict)
    tail = {}
    buckets = defaultdict(list)
    duplicates = 0
    with path.open(encoding='utf8', errors='replace') as source:
        for raw in source:
            match = LINE.search(raw)
            if not match:
                continue
            text = match[1]
            if text.startswith('LOOP_OPS '):
                f = fields(text)
                year, post = f.get('y'), f.get('post')
                if year in YEARS and post is not None:
                    if post in loop[year]:
                        duplicates += 1
                    loop[year][post] = f
            elif text.startswith('TAIL_SHADOW '):
                f = fields(text)
                year = f.get('y')
                if year not in YEARS:
                    continue
                if f.get('kind') == 'total':
                    if year in tail:
                        duplicates += 1
                    tail[year] = f
                elif f.get('kind') == 'bucket':
                    buckets[year].append(f)
    years = {}
    for year in YEARS:
        li = loop[year]
        t = tail.get(year, {})
        n = int(li.get('tail_shadow', {}).get('n', 0))
        sum_buckets = sum(x.get('n', 0) for x in buckets[year])
        none_key = 'none|rail_none|rq_no|c67_off'
        unknown_after = sum(x.get('cap_after', 0) for x in buckets[year]
                            if x.get('state') != none_key)
        known_none_after = sum(x.get('cap_after', 0) for x in buckets[year]
                               if x.get('state') == none_key)
        years[str(year)] = {
            'loops': int(li.get('sleep_left', {}).get('n', 0)),
            'sleep_left': int(li.get('sleep_left', {}).get('ops', 0)),
            'raw_cap': int(sum(v.get('ops', 0) for k, v in li.items()
                               if str(k).startswith('sleep_cap3k_'))),
            'shadow_ops': int(li.get('tail_shadow', {}).get('ops', 0)),
            'shadow_ticks_crossed': int(li.get('tail_shadow', {}).get('tk', 0)),
            'shadow_calls': n,
            'total': t,
            'buckets': buckets[year],
            'bucket_sample_sum': sum_buckets,
            'unknown_after_cap': unknown_after,
            'none_after_cap': known_none_after,
            'valid_sample_accounting': (
                bool(t) and t.get('high', 0) + t.get('low', 0) == n
                and sum_buckets == t.get('high', 0)
                and unknown_after + known_none_after == t.get('after_cap', 0)),
        }
    return years, duplicates


def analyze(directory, seeds, variant_id='p0_tail_shadow_diagnostic'):
    by_seed = {}
    for seed in seeds:
        per_arm = {}
        for arm, prefix in (('reference', 'reference'), ('variant', variant_id)):
            name = f'{prefix}_seed{seed}_r0.log'
            source = directory / name
            if not source.is_file():
                raise FileNotFoundError(source)
            annual, duplicate = read_log(source)
            per_arm[arm] = {'yearly': annual, 'duplicate_records': duplicate}
        by_seed[str(seed)] = per_arm
    average = {}
    fields_numeric = ('loops', 'sleep_left', 'raw_cap', 'shadow_ops',
                      'shadow_ticks_crossed', 'shadow_calls',
                      'unknown_after_cap', 'none_after_cap')
    t_numeric = ('high','low','crosses','guard_ops','guard_max',
                 'before_cap','after_cap','unknown','other')
    for year in YEARS:
        average[str(year)] = {}
        for arm in ('reference','variant'):
            values = [by_seed[str(s)][arm]['yearly'][str(year)] for s in seeds]
            avg = {k: round(statistics.mean(v[k] for v in values), 2)
                   for k in fields_numeric}
            if arm == 'variant':
                avg['sample'] = {k: round(statistics.mean(v['total'].get(k,0)
                                                        for v in values), 2)
                                 for k in t_numeric}
                avg['all_samples_reconciled'] = all(v['valid_sample_accounting']
                                                    for v in values)
            average[str(year)][arm] = avg
    return {'seeds':seeds,'by_seed':by_seed,'annual_mean':average,
            'limitations': ['A/B arms can diverge economically and in scheduler trajectory; compare same-seed values descriptively only.',
                            'TAIL_SHADOW.before_cap is not actually runnable work, after_cap subtracts internal guard only.',
                            'UNKNOWN means potentially pending but no certified readiness; zero recovered worker opcodes.',
                            'tail_shadow_ticks_crossed covers full hook metering, not the narrower crosses within guard.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('engine_logs', type=Path)
    p.add_argument('--seeds', nargs='+', type=int, default=[42,100,999,1234,5678])
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    report = analyze(args.engine_logs, args.seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    for year, d in report['annual_mean'].items():
        v = d['variant']; t = v['sample']
        print(year, 'shadow_ops',v['shadow_ops'], 'shadow_ticks',v['shadow_ticks_crossed'],
              'before',t['before_cap'], 'after',t['after_cap'],
              'unknown',t['unknown'], 'all_samples_reconciled',v['all_samples_reconciled'])


if __name__ == '__main__':
    main()
