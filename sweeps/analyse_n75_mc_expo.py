"""Diagnostic N75-MC: de-duplicate actual rail/air builds by seed+physical OD.

Usage: python -X utf8 sweeps/analyse_n75_mc_expo.py <campaign> [--year 1972]
Paired build differences are observations, NOT causal profit estimates.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE = re.compile(r'OPEX\s+(\d{4})-\d{1,2}-\d{1,2}\s+([A-Z][A-Z0-9_]*)\s+(.*)')
FIELD = re.compile(r'([a-z_]+)=([^ ]+)')
BUILD = {'RAIL_BUILD', 'AIR_BUILD'}


def read_log(path, year):
    out = {'rail': {}, 'air': {}, 'n75': Counter(), 'ops': 0,
           'budget_eligible': 0, 'refill': 0, 'unapplied': 0}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        match = TRACE.search(line)
        if not match or int(match.group(1)) != year:
            continue
        tag, payload = match.group(2), match.group(3)
        if tag != 'N75_MC' and tag not in BUILD:
            continue
        f = dict(FIELD.findall(payload))
        if tag == 'N75_MC':
            phase = f.get('phase', 'unknown')
            out['n75'][phase] += 1
            if phase == 'refill':
                out['refill'] += 1
                out['ops'] += max(0, int(f.get('ops', '0')))
                out['budget_eligible'] += int(f.get('budget_eligible', '0'))
            if phase == 'unapplied':
                out['unapplied'] += 1
            continue
        src, dst = f.get('src'), f.get('dst')
        if src is None or dst is None:
            continue
        cargo = f.get('cargo', 'PASS') if tag == 'RAIL_BUILD' else 'PASS'
        key = (cargo, src, dst) if tag == 'RAIL_BUILD' else ('PASS',) + tuple(sorted((src, dst)))
        d = {'line': f.get('line'), 'pred_profit': int(f.get('pred_profit', f.get('profit', '0'))),
             'cost': int(f.get('cost', '0')), 'src': src, 'dst': dst, 'cargo': cargo}
        out['rail' if tag == 'RAIL_BUILD' else 'air'].setdefault(key, d)
    return out


def analyze(campaign, year):
    engine = ROOT / 'results' / (campaign + '_engine')
    if not engine.is_dir():
        raise FileNotFoundError(engine)
    files = {}
    for arm, prefix in [('off', 'reference'), ('on', 'n75_mc')]:
        for path in engine.glob(prefix + '_seed*_r0.log'):
            seed = re.search(r'_seed(\d+)_r0\.log$', path.name)
            if seed:
                files[(arm, int(seed.group(1)))] = path
    seeds = sorted({seed for arm, seed in files if arm == 'off'} &
                   {seed for arm, seed in files if arm == 'on'})
    summary = {'campaign': campaign, 'year': year, 'seeds': seeds, 'per_seed': []}
    for seed in seeds:
        off = read_log(files[('off', seed)], year)
        on = read_log(files[('on', seed)], year)
        r_added = set(on['rail']) - set(off['rail'])
        r_lost = set(off['rail']) - set(on['rail'])
        a_added = set(on['air']) - set(off['air'])
        a_lost = set(off['air']) - set(on['air'])
        detail = {
            'seed': seed, 'off_rail': len(off['rail']), 'on_rail': len(on['rail']),
            'added_rail': [on['rail'][k] for k in sorted(r_added)],
            'lost_rail': [off['rail'][k] for k in sorted(r_lost)],
            'off_air': len(off['air']), 'on_air': len(on['air']),
            'added_air': [on['air'][k] for k in sorted(a_added)],
            'lost_air': [off['air'][k] for k in sorted(a_lost)],
            'on_n75_phases': dict(on['n75']), 'off_n75_phases': dict(off['n75']),
            'refill': on['refill'], 'unapplied': on['unapplied'],
            'budget_eligible_events': on['budget_eligible'], 'n75_logged_ops': on['ops'],
        }
        summary['per_seed'].append(detail)
    summary['total'] = {
        'paired_seeds': len(seeds),
        'on_refill': sum(s['refill'] for s in summary['per_seed']),
        'on_unapplied': sum(s['unapplied'] for s in summary['per_seed']),
        'on_budget_eligible': sum(s['budget_eligible_events'] for s in summary['per_seed']),
        'added_rail': sum(len(s['added_rail']) for s in summary['per_seed']),
        'lost_rail': sum(len(s['lost_rail']) for s in summary['per_seed']),
        'added_air': sum(len(s['added_air']) for s in summary['per_seed']),
        'lost_air': sum(len(s['lost_air']) for s in summary['per_seed']),
        'n75_logged_ops': sum(s['n75_logged_ops'] for s in summary['per_seed']),
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('campaign')
    parser.add_argument('--year', type=int, default=1972)
    args = parser.parse_args()
    print(json.dumps(analyze(args.campaign, args.year), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
