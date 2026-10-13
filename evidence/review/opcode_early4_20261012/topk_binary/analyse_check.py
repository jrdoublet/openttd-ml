"""Parité comparative P0 Top-K, mesures au runtime sur entrées identiques.

Les chiffres sont des fenêtres de budget AI mesurées dans une campagne
check=1. Le contrôle exécute deux chemins et perturbe la simulation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


RECORD = re.compile(r'\[script:\d+\] \[0\] \[I\] P0_TOPK_BINARY '
                    r'year=(\d+) calls=(\d+) old_ops=(\d+) '
                    r'new_ops=(\d+) mismatches=(\d+)')


def analyse(directory, seeds):
    result = {}
    for seed in seeds:
        source = directory / f'p0_topk_check_seed{seed}_r0.log'
        if not source.is_file():
            raise FileNotFoundError(source)
        by_year = {}
        for line in source.read_text(encoding='utf8', errors='replace').splitlines():
            m = RECORD.search(line)
            if not m:
                continue
            year, calls, old, new, mismatch = map(int, m.groups())
            if year in by_year:
                raise ValueError(f'Duplicate annual register seed={seed} y={year}')
            by_year[year] = dict(calls=calls, old_ops=old, new_ops=new,
                                 mismatches=mismatch,
                                 reduction_pct=round(100*(old-new)/old,4) if old else None)
        result[str(seed)] = {str(y): by_year[y] for y in sorted(by_year)}
    return {'seeds':seeds, 'by_seed':result,
            'all_mismatches':sum(z['mismatches'] for s in result.values() for z in s.values()),
            'calls':sum(z['calls'] for s in result.values() for z in s.values()),
            'old_ops':sum(z['old_ops'] for s in result.values() for z in s.values()),
            'new_ops':sum(z['new_ops'] for s in result.values() for z in s.values()),
            'limitations':['Instrumented time-window opcodes, not actual Squirrel instructions.',
                           'A check trace preserves the historical chosen list but pays both comparator costs.',
                           '5 years are necessary to close register 1973; coverage per seed/year must be complete.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('engine_logs', type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--seeds', nargs='+', type=int, default=[42,100,999,1234,5678])
    args = p.parse_args()
    result = analyse(args.engine_logs, args.seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('calls',result['calls'],'mismatches',result['all_mismatches'],
          'old_ops',result['old_ops'],'new_ops',result['new_ops'])
    for s, rows in result['by_seed'].items():
        print('seed',s,rows)


if __name__ == '__main__':
    main()
