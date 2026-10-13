#!/usr/bin/env python3
"""Audit descriptif du portefeuille P2/P5, par année, sur journaux existants.

P2_PASS est une photo APRES dispatch, P5_RAIL_PASS inspecte le vivier
après le dispatch. Les causes de refus passStop ne sont PAS des raisons
d'échec de construction ; le compteur in_best vient d'avant la tâche.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from analyse_opcode_early4 import LINE, DATE, YEARS, fields


def inspect(stream):
    buckets = defaultdict(lambda: {
        'passes': 0, 'start_empty': 0, 'start_nonempty_no_build': 0,
        'passes_built': 0, 'units_built': 0,
        'post_empty': 0, 'reasons': Counter(),
        'rail_passes': 0, 'rail_pool_nonempty_after': 0,
        'rail_fundable_after': 0, 'rail_selected_after': 0,
        'rail_constructed': 0, 'rail_no_alternatives_after': 0,
        'rail_alternatives_total_after': 0,
        'wait_started': 0, 'wait_immediate': 0,
        'wait_resolved': 0, 'wait_days_total': 0,
        'wait_resolved_by': Counter(),
    })
    months = defaultdict(lambda: defaultdict(Counter))
    for raw in stream:
        m = LINE.search(raw)
        if not m:
            continue
        d = DATE.match(m[1])
        if not d:
            continue
        year, kind, rest = int(d[1]), d[2], d[3]
        if year not in YEARS:
            continue
        month = int(m[1].split(' ', 2)[1].split('-')[1])
        row = fields(rest)
        x = buckets[year]
        if kind == 'P2_PASS':
            month_values = months[year][month]
            month_values['passes'] += 1
            month_values['initial_pool_empty'] += row.get('in_best') == 0
            month_values['post_pool_empty'] += row.get('post_best') == 0
            month_values['passes_with_physical_progress'] += row.get('n_built', 0) > 0
            x['passes'] += 1
            x['start_empty'] += row.get('in_best') == 0
            x['start_nonempty_no_build'] += row.get('in_best', 0) > 0 and row.get('n_built', 0) == 0
            x['passes_built'] += row.get('n_built', 0) > 0
            x['units_built'] += row.get('n_built', 0)
            x['post_empty'] += row.get('post_best') == 0
            x['reasons'][str(row.get('stop', 'unknown'))] += 1
        elif kind == 'P5_RAIL_PASS':
            month_values = months[year][month]
            month_values['rail_nonempty_after'] += row.get('rail_alts', 0) > 0
            month_values['rail_fundable_after'] += row.get('rail_aff') == 1
            month_values['rail_selected_after'] += row.get('rail_in_best', 0) > 0
            month_values['rail_built'] += row.get('rail_built', 0)
            x['rail_passes'] += 1
            x['rail_pool_nonempty_after'] += row.get('rail_alts', 0) > 0
            x['rail_no_alternatives_after'] += row.get('alts') == 0
            x['rail_fundable_after'] += row.get('rail_aff') == 1
            x['rail_selected_after'] += row.get('rail_in_best', 0) > 0
            x['rail_constructed'] += row.get('rail_built', 0)
            x['rail_alternatives_total_after'] += row.get('rail_alts', 0)
        elif kind == 'P5_WAIT_START':
            x['wait_started'] += 1
        elif kind == 'P2_RESOLVE':
            # A waiting episode may start in 1972 and resolve in 1973;
            # report closing-year only and keep that limitation explicit.
            # Immediate P2_RESOLVE is printed for nonempty best just built.
            if row.get('ret_reason') == 'immediate':
                x['wait_immediate'] += 1
            else:
                x['wait_resolved'] += 1
                x['wait_days_total'] += row.get('days', 0)
                x['wait_resolved_by'][str(row.get('ret_task', 'unknown'))] += 1
    return {str(y): {**{k: dict(v) if isinstance(v, Counter) else v
                         for k, v in buckets[y].items()},
                      'months': {str(m): dict(c) for m, c in sorted(months[y].items())}}
            for y in YEARS}


def analyze(directory, seeds):
    by_seed = {}
    for seed in seeds:
        matches = list(directory.glob(f'*seed{seed}_r0.log'))
        if len(matches) != 1:
            raise ValueError(f'seed={seed} expected exactly one log, got {len(matches)}')
        with matches[0].open(encoding='utf-8', errors='replace') as f:
            by_seed[str(seed)] = inspect(f)
    avg = {}
    keys = [k for k, v in by_seed[str(seeds[0])][str(YEARS[0])].items()
            if isinstance(v, int)]
    for year in YEARS:
        avg[str(year)] = {k: round(statistics.mean(by_seed[str(s)][str(year)][k]
                                                       for s in seeds), 2) for k in keys}
    return {'by_seed': by_seed, 'average': avg, 'seeds': seeds,
            'cautions': ['P2_PASS counters are physical delta only, may count fleet vehicle purchases and omit scrapped lines.',
                         'P5_RAIL_PASS alternatives/financing are recorded AFTER the projects dispatch; do not read as its input.',
                         'P2 stop is an observational label based on in_best and built delta; not a root-cause reason. Initial empty pool in 1972 is overwhelmingly seed42, in 1973 seed100.',
                         'P2_RESOLVE waiting episodes can cross accounting years; resolution attributed to closing year.',
                         'Profiled seed trajectories cannot be combined with the unsounded economic reference as one game.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('logs', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seeds', nargs='+', type=int, default=[42,100,999,1234,5678])
    args = ap.parse_args()
    data = analyze(args.logs, args.seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for year, row in data['average'].items():
        print(year, row)


if __name__ == '__main__':
    main()
