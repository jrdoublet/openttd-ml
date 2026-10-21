#!/usr/bin/env python3
"""
rail_ech_autopsy.py: Autopsie detaillee des 39 abandons A* rail OpexAI vs AAAHogEx.
Analyse les 6 parties x 10 ans (graines 42, 7, 1234 des deux campagnes v270 et v265fix).
Deduplication strictement identique a sweeps/rail_ech_fail_cmp.py:
k = (f, line.split('] [I] ')[-1][:10], m[1])
"""

import gzip
import re
import sys
import glob
import collections
import statistics

FILES = [
    # v270 expo reference
    "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v270/results/v270_expo_3x10_20261019_engine/reference_seed42_r0.log.gz",
    "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v270/results/v270_expo_3x10_20261019_engine/reference_seed7_r0.log.gz",
    "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v270/results/v270_expo_3x10_20261019_engine/reference_seed1234_r0.log.gz",
    # v265fix expo reference
    "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v265fix/results/v265fix_expo_complete_3x10_20261019_engine/reference_seed42_r0.log.gz",
    "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v265fix/results/v265fix_expo_complete_3x10_20261019_engine/reference_seed7_r0.log.gz",
    "/home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v265fix/results/v265fix_expo_complete_3x10_20261019_engine/reference_seed1234_r0.log.gz",
]

BINS = [(0, 60), (60, 100), (100, 160), (160, 250), (250, 9999)]

def get_bin(d):
    for lo, hi in BINS:
        if lo <= d < hi:
            return f"{lo}-{hi if hi < 9999 else '+'}"
    return "unknown"

def parse_all():
    opex_attempts = []
    aaa_attempts = []
    aaa_path_founds = []
    seen_opex = set()
    
    for f in FILES:
        camp = "v270" if "wt-v270" in f else "v265fix"
        m_seed = re.search(r'reference_seed(\d+)_r0', f)
        seed = int(m_seed.group(1)) if m_seed else 0
        
        with gzip.open(f, 'rt', errors='replace') as gz:
            for line in gz:
                if '[script:4] [0]' in line and 'RAIL_ATTEMPT' in line:
                    # Match pattern like rail_ech_fail_cmp.py
                    m_cmp = re.search(r'RAIL_ATTEMPT (src=\S+ dst=\S+).*?manh=(\d+).*?ok=(\d) reason=(\S+)', line)
                    if not m_cmp:
                        continue
                    
                    k = (f, line.split('] [I] ')[-1][:10], m_cmp.group(1))
                    if k in seen_opex:
                        continue
                    seen_opex.add(k)
                    
                    # Full parse of line
                    m = re.search(r'OPEX (\d{4}-\d{1,2}-\d{1,2}) RAIL_ATTEMPT src=(\d+) dst=(\d+) kind=(\S+) manh=(\d+) reuse=(\d+) join_end=(\S+) shared_dest=(\d+) pred_profit=(-?\d+) pred_roi=(-?\d+) pred_astar=(\d+) pre=(\d+) model=(\d+) quote=(-?\d+) actual=(-?\d+) ok=(\d) reason=(\S+) iters=(\d+) ops=(\d+) search_ops=(\d+) startx=(-?\d+) endx=(-?\d+) weight=(\d+)', line)
                    if not m:
                        continue
                    
                    date_str = m.group(1)
                    src = int(m.group(2))
                    dst = int(m.group(3))
                    kind = m.group(4)
                    manh = int(m.group(5))
                    reuse = int(m.group(6))
                    join_end = m.group(7)
                    shared_dest = int(m.group(8))
                    pred_profit = int(m.group(9))
                    pred_roi = int(m.group(10))
                    pred_astar = int(m.group(11))
                    pre = int(m.group(12))
                    model = int(m.group(13))
                    quote = int(m.group(14))
                    actual = int(m.group(15))
                    ok = int(m.group(16))
                    reason = m.group(17)
                    iters = int(m.group(18))
                    ops = int(m.group(19))
                    search_ops = int(m.group(20))
                    startx = int(m.group(21))
                    endx = int(m.group(22))
                    weight = int(m.group(23))
                    
                    year = int(date_str.split('-')[0])
                    
                    opex_attempts.append({
                        'camp': camp,
                        'file': f,
                        'seed': seed,
                        'date': date_str,
                        'year': year,
                        'src': src,
                        'dst': dst,
                        'kind': kind,
                        'manh': manh,
                        'reuse': reuse,
                        'join_end': join_end,
                        'shared_dest': shared_dest,
                        'pred_profit': pred_profit,
                        'pred_roi': pred_roi,
                        'pred_astar': pred_astar,
                        'pre': pre,
                        'model': model,
                        'quote': quote,
                        'actual': actual,
                        'ok': ok,
                        'reason': reason,
                        'iters': iters,
                        'ops': ops,
                        'search_ops': search_ops,
                        'startx': startx,
                        'endx': endx,
                        'weight': weight,
                        'bin': get_bin(manh),
                    })
                
                elif '[script:4] [1]' in line and '# RouteBuilder ' in line and 'RailRoute' in line:
                    m = re.search(r'# RouteBuilder (Failed|Succeeded) (\S+) (\S+) (\d+)(.*)', line)
                    if m:
                        status = m.group(1)
                        route_type = m.group(2)
                        line_id = m.group(3)
                        dist = int(m.group(4))
                        rest = m.group(5).strip()
                        aaa_attempts.append({
                            'camp': camp,
                            'seed': seed,
                            'status': status,
                            'route_type': route_type,
                            'line_id': line_id,
                            'dist': dist,
                            'rest': rest,
                            'bin': get_bin(dist),
                            'raw': line.strip()
                        })
                
                elif '[script:4] [1]' in line and 'TrainRoute: Path found' in line:
                    m = re.search(r'(\d{4}-\d{1,2}-\d{1,2}) TrainRoute: Path found\. \(count:(\d+) date:(\d+)\) distance:(\d+)', line)
                    if m:
                        aaa_path_founds.append({
                            'camp': camp,
                            'seed': seed,
                            'date': m.group(1),
                            'year': int(m.group(1).split('-')[0]),
                            'count': int(m.group(2)),
                            'days': int(m.group(3)),
                            'dist': int(m.group(4)),
                            'bin': get_bin(int(m.group(4))),
                        })

    return opex_attempts, aaa_attempts, aaa_path_founds

def main():
    opex, aaa, aaa_paths = parse_all()
    print(f"Opex attempts total: {len(opex)}")
    print(f"AAA RouteBuilder total: {len(aaa)}")
    print(f"AAA PathFound total: {len(aaa_paths)}")
    
    # 1. Verification of global numbers
    op_ok = [a for a in opex if a['ok'] == 1]
    op_fail = [a for a in opex if a['ok'] == 0]
    print(f"Opex: {len(op_ok)}/{len(opex)} ({100*len(op_ok)/len(opex):.1f}%)")
    reasons = collections.Counter(a['reason'] for a in op_fail)
    print("Opex failure reasons:", dict(reasons))
    
    aaa_ok = [a for a in aaa if a['status'] == 'Succeeded']
    print(f"AAA: {len(aaa_ok)}/{len(aaa)} ({100*len(aaa_ok)/len(aaa):.1f}%)")
    
    # Distance breakdown
    print("\nDistance breakdown:")
    for lo, hi in BINS:
        b_name = f"{lo}-{hi if hi < 9999 else '+'}"
        op_b = [a for a in opex if a['bin'] == b_name]
        op_b_ok = [a for a in op_b if a['ok'] == 1]
        aaa_b = [a for a in aaa if a['bin'] == b_name]
        aaa_b_ok = [a for a in aaa_b if a['status'] == 'Succeeded']
        print(f"  {b_name:<10}: Opex {len(op_b_ok)}/{len(op_b)} ({100*len(op_b_ok)/max(len(op_b),1):.0f}%) | AAA {len(aaa_b_ok)}/{len(aaa_b)} ({100*len(aaa_b_ok)/max(len(aaa_b),1):.0f}%)")
        
    # Iters comparison
    print("\nIters comparison (median, min-max):")
    for lo, hi in BINS:
        b_name = f"{lo}-{hi if hi < 9999 else '+'}"
        op_b_ok = [a['iters'] for a in opex if a['bin'] == b_name and a['ok'] == 1]
        op_b_abnd = [a['iters'] for a in opex if a['bin'] == b_name and a['reason'] == 'ABND']
        aaa_b_counts = [p['count'] for p in aaa_paths if p['bin'] == b_name]
        aaa_b_days = [p['days'] for p in aaa_paths if p['bin'] == b_name]
        
        ok_m = f"{statistics.median(op_b_ok):.0f} [{min(op_b_ok)}-{max(op_b_ok)}] (n={len(op_b_ok)})" if op_b_ok else "-"
        abnd_m = f"{statistics.median(op_b_abnd):.0f} [{min(op_b_abnd)}-{max(op_b_abnd)}] (n={len(op_b_abnd)})" if op_b_abnd else "-"
        aaa_m = f"{statistics.median(aaa_b_counts):.0f} calls ({statistics.median(aaa_b_counts)*50:.0f} it), {statistics.median(aaa_b_days):.0f}j (n={len(aaa_b_counts)})" if aaa_b_counts else "-"
        print(f"  {b_name:<10}: OK med={ok_m} | ABND med={abnd_m} | AAA med={aaa_m}")

    # List all 39 ABNDs
    abnds = [a for a in opex if a['reason'] == 'ABND']
    print(f"\nExact list of the {len(abnds)} ABND attempts:")
    for i, a in enumerate(abnds, 1):
        print(f"  {i:2d}. {a['camp']} s{a['seed']} {a['date']} {a['kind']:<7} src={a['src']} dst={a['dst']} manh={a['manh']:3d} profit={a['pred_profit']:6d} roi={a['pred_roi']:4d} weight={a['weight']:3d} iters={a['iters']} ops={a['ops']/1e6:.1f}M")

if __name__ == '__main__':
    main()
