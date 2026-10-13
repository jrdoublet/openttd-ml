#!/usr/bin/env python3
"""Reconcile exclusive SPAN tree costs; experimental only.

All opcodes are tick-based window charges; A* or commands can traverse ticks.
SPAN_AGG children are independent internal subinterval observations and
must not be added to SPAN totals. Orphans and malformed trees are reported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from analyse_opcode_early4 import LINE, DATE, fields, YEARS
from analyse_projects_passes_early4 import distribution


def parse(stream):
    spans = {}
    aggs = defaultdict(list)
    duplicate = 0
    for raw in stream:
        m = LINE.search(raw)
        if m is None:
            continue
        d = DATE.match(m[1])
        if d is None or int(d[1]) not in range(1970, 1980):
            continue
        kind = d[2]
        if kind not in ('SPAN', 'SPAN_AGG'):
            continue
        f = fields(d[3])
        if kind == 'SPAN':
            if not all(k in f for k in ('id', 'par', 'op', 'tk', 'n')):
                continue
            sid = f['id']
            if sid in spans:
                duplicate += 1
                continue
            begin_year = int(str(f.get('ds', '')).split('-', 1)[0]) if 'ds' in f else int(d[1])
            spans[sid] = {'id': sid, 'par': f['par'], 'name': str(f['n']),
                          'start_year': begin_year, 'end_year': int(d[1]),
                          'op': f['op'], 'ticks': f['tk'],
                          'orphan': f.get('orphan', 0) == 1,
                          't0': f.get('t0')}
        elif all(k in f for k in ('par','n','cnt','op')):
            aggs[f['par']].append({'name': str(f['n']), 'cnt': f['cnt'],
                                   'op': f['op'], 'ticks': f.get('tk')})
    children = defaultdict(list)
    missing_parents = 0
    for sid, row in spans.items():
        if row['par'] == 0:
            continue
        if row['par'] not in spans:
            missing_parents += 1
            continue
        children[row['par']].append(sid)
    invalid_exclusive = 0
    for sid, row in spans.items():
        direct_ops = sum(spans[child]['op'] for child in children[sid])
        row['children'] = len(children[sid])
        row['exclusive_ops'] = row['op'] - direct_ops
        row['aggregates'] = aggs.get(sid, [])
        if row['exclusive_ops'] < 0:
            invalid_exclusive += 1
    return spans, {'duplicate_ids': duplicate, 'missing_parents': missing_parents,
                   'negative_exclusive': invalid_exclusive,
                   'aggregate_without_span': len(set(aggs) - set(spans)),
                   'orphan_spans': sum(row['orphan'] for row in spans.values())}


def summarize(spans):
    result = {}
    for year in YEARS:
        selected = [row for row in spans.values() if row['end_year'] == year
                    and not row['orphan'] and row['exclusive_ops'] >= 0]
        output = {}
        for name in sorted(set(row['name'] for row in selected)):
            rows = [r for r in selected if r['name'] == name]
            output[name] = {
                'inclusive': distribution([r['op'] for r in rows]),
                'exclusive': distribution([r['exclusive_ops'] for r in rows]),
                'same_tick': sum(r['ticks'] == 0 for r in rows),
                'crossed_tick': sum(r['ticks'] != 0 for r in rows),
                'start_year_mismatch': sum(r['start_year'] != year for r in rows),
            }
        aggregate_by_name = defaultdict(lambda: {'calls': 0, 'ops': 0, 'ticks': 0})
        for row in selected:
            for a in row['aggregates']:
                x = aggregate_by_name[a['name']]
                x['calls'] += a['cnt']
                x['ops'] += a['op']
                x['ticks'] += a.get('ticks') or 0
        result[str(year)] = {'spans': output, 'intra_span_aggregates': dict(aggregate_by_name)}
    return result


def run(folder, seeds, prefix=None):
    by_seed = {}
    for seed in seeds:
        logs = ([folder / f'{prefix}_seed{seed}_r0.log'] if prefix is not None
                else list(folder.glob(f'*seed{seed}_r0.log')))
        if len(logs) != 1:
            raise ValueError(f'seed={seed}: need exactly one trace, found {len(logs)}')
        if not logs[0].is_file():
            raise FileNotFoundError(logs[0])
        with logs[0].open(encoding='utf8', errors='replace') as fh:
            spans, diagnostic = parse(fh)
        by_seed[str(seed)] = {'data': summarize(spans), 'quality': diagnostic}
    return {'by_seed': by_seed, 'seeds': seeds,
            'method': ('All intervals are tick-accounted, not actual VM instructions. '
                       'Parent includes child; exclusive only subtracts direct nested SPAN children. '
                       'SPAN_AGG values are not added to any interval. Orphan spans are omitted. '
                       'Instrumenting every span can perturb the simulation; never merge profiled '
                       'and unsounded economics as a single trajectory.')}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seeds', nargs='+', type=int, default=[42])
    p.add_argument('--prefix', default=None,
                   help='Exact campaign arm logfile prefix for A/B engine directories')
    args = p.parse_args()
    value = run(args.logs, args.seeds, args.prefix)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for seed, row in value['by_seed'].items():
        print('seed', seed, 'quality', row['quality'])
        for year, yr in row['data'].items():
            for key in ('select.reselect', 'select.incremental', 'select.full',
                        'projects.post_regen.incremental', 'fleet.resize'):
                if key in yr['spans']:
                    print(year, key, yr['spans'][key])


if __name__ == '__main__':
    main()
