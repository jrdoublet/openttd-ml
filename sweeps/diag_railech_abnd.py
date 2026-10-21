#!/usr/bin/env python3
"""
diag_railech_abnd.py - Analyse comparative des tentatives rail et abandons A*
entre OpexAI (master vs v299 adapt=400) et AAAHogEx sur les journaux v299 (10 ans, 3 graines).
"""

import os
import sys
import glob
import re
import statistics
import collections

DEFAULT_DIR = "/home/deploy/projects/wt-v299/results/v299_diag_3x10_20261021_engine"
SLICES = [("<60", 0, 60), ("60-100", 60, 100), ("100-160", 100, 160), (">=160", 160, 99999)]

def get_slice(d):
    for label, lo, hi in SLICES:
        if lo <= d < hi:
            return label
    return ">=160"

def parse_opex_attempt(line, arm, seed, filename):
    parts = {}
    for token in line.strip().split():
        if "=" in token:
            k, v = token.split("=", 1)
            parts[k] = v
    if "manh" not in parts or "reason" not in parts:
        return None
    
    date_str = line.split("OPEX ")[1].split(" ")[0] if "OPEX " in line else ""
    manh = int(parts.get("manh", 0))
    src = int(parts.get("src", 0))
    dst = int(parts.get("dst", 0))
    return {
        "arm": arm,
        "seed": seed,
        "file": filename,
        "date": date_str,
        "src": src,
        "dst": dst,
        "src_coord": (src % 256, src // 256),
        "dst_coord": (dst % 256, dst // 256),
        "kind": parts.get("kind", ""),
        "manh": manh,
        "slice": get_slice(manh),
        "reuse": int(parts.get("reuse", 0)),
        "join_end": parts.get("join_end", "-"),
        "shared_dest": int(parts.get("shared_dest", 0)),
        "pred_profit": int(parts.get("pred_profit", 0)),
        "pred_roi": int(parts.get("pred_roi", 0)),
        "ok": int(parts.get("ok", 0)),
        "reason": parts.get("reason", ""),
        "iters": int(parts.get("iters", 0)),
        "ops": int(parts.get("ops", 0)),
        "search_ops": int(parts.get("search_ops", 0)),
        "weight": int(parts.get("weight", 0)),
        "adapt": parts.get("adapt", "-"),
        "len": int(parts.get("len", -1)),
    }

def parse_logs(log_dir):
    files = sorted(glob.glob(os.path.join(log_dir, "*.log")))
    if not files:
        files = sorted(glob.glob(os.path.join(log_dir, "*.log.gz")))
    
    data = {
        "opex": {"reference": [], "v299": []},
        "aaa_routes": {"reference": [], "v299": []},
        "aaa_paths": {"reference": [], "v299": []},
    }

    for fpath in files:
        fname = os.path.basename(fpath)
        arm = "reference" if "reference" in fname else "v299"
        m_seed = re.search(r"seed(\d+)", fname)
        seed = int(m_seed.group(1)) if m_seed else 0
        
        opener = open
        if fpath.endswith(".gz"):
            import gzip
            opener = lambda p: gzip.open(p, "rt", errors="replace")
        else:
            opener = lambda p: open(p, "r", errors="replace")
            
        with opener(fpath) as fp:
            lines = fp.readlines()
            
        for idx, line in enumerate(lines):
            # Opex RAIL_ATTEMPT
            if "[script:4] [0]" in line and "RAIL_ATTEMPT" in line:
                att = parse_opex_attempt(line, arm, seed, fname)
                if att:
                    data["opex"][arm].append(att)
                    
            # AAA RouteBuilder RailRoute
            elif "[script:4] [1]" in line and "# RouteBuilder " in line and "RailRoute" in line:
                m = re.search(r"# RouteBuilder (Succeeded|Failed) (\d+) (\d+) (\d+) Build RailRoute (.*)", line)
                if m:
                    status = m.group(1)
                    vtype = int(m.group(2))
                    days = int(m.group(3))
                    dist = int(m.group(4))
                    route = m.group(5).strip()
                    
                    cause = status
                    if status == "Failed":
                        for j in range(idx - 1, max(0, idx - 100), -1):
                            if "[1]" in lines[j]:
                                lj = lines[j]
                                if "RailPathBuilder: No path found" in lj:
                                    cause = "A* No path found"
                                    break
                                elif "RailPathBuilder: railBuilder1.Build failed" in lj:
                                    cause = "Build failed"
                                    break
                                elif "TrainRoute: No destStation" in lj:
                                    cause = "No destStation"
                                    break
                                elif "TrainRoute: No srcStation" in lj:
                                    cause = "No srcStation"
                                    break
                                elif "TrainRoute: srcHgStation.BuildExec failed" in lj:
                                    cause = "srcStation.BuildExec failed"
                                    break
                                elif "TrainRoute: destHgStation.BuildExec failed" in lj:
                                    cause = "destStation.BuildExec failed"
                                    break
                                elif "TrainRoute: srcDepot == null" in lj:
                                    cause = "srcDepot == null"
                                    break
                                elif "AddNgPlace" in lj:
                                    cause = "Station NG (AddNgPlace)"
                                    break
                                elif "# RouteBuilder Start" in lj:
                                    break
                    data["aaa_routes"][arm].append({
                        "arm": arm,
                        "seed": seed,
                        "file": fname,
                        "status": status,
                        "cause": cause,
                        "days": days,
                        "dist": dist,
                        "slice": get_slice(dist),
                        "route": route,
                    })
                    
            # AAA TrainRoute: Path found
            elif "[script:4] [1]" in line and "TrainRoute: Path found" in line:
                m = re.search(r"TrainRoute: Path found\. \(count:(\d+) date:(\d+)\) distance:(\d+)", line)
                if m:
                    count = int(m.group(1))
                    days = int(m.group(2))
                    dist = int(m.group(3))
                    data["aaa_paths"][arm].append({
                        "arm": arm,
                        "seed": seed,
                        "count": count,
                        "iters": count * 50,
                        "days": days,
                        "dist": dist,
                        "slice": get_slice(dist),
                    })
                    
    return data

def print_report(data):
    print("=" * 80)
    print("DIAGNOSTIC RAIL-ECH : OPEXAI VS AAAHOGEX SUR LES JOURNAUX V299 (3 SEEDS X 10 ANS)")
    print("=" * 80)
    
    for arm in ["reference", "v299"]:
        arm_title = "MASTER (reference: weight 120 under 100, 200 above)" if arm == "reference" else "V299 (v294_rail_weight_adapt=400)"
        attempts = data["opex"][arm]
        print(f"\n--- OPEXAI : {arm_title} (N={len(attempts)}) ---")
        
        reasons = sorted(list(set(a["reason"] for a in attempts)))
        header = f"{'Motif':<12}" + "".join([f"{label:>10}" for label, _, _ in SLICES]) + f"{'Total':>10}"
        print(header)
        print("-" * len(header))
        for r in reasons:
            row = f"{r:<12}"
            tot_r = 0
            for label, _, _ in SLICES:
                cnt = sum(1 for a in attempts if a["reason"] == r and a["slice"] == label)
                tot_r += cnt
                row += f"{cnt:>10}"
            row += f"{tot_r:>10}"
            print(row)
        print("-" * len(header))
        tot_row = f"{'TOTAL':<12}"
        for label, _, _ in SLICES:
            cnt = sum(1 for a in attempts if a["slice"] == label)
            tot_row += f"{cnt:>10}"
        tot_row += f"{len(attempts):>10}"
        print(tot_row)
        
        ok_cnt = sum(1 for a in attempts if a["ok"] == 1)
        print(f"\nTaux de succès OpexAI : {ok_cnt}/{len(attempts)} ({ok_cnt/max(1, len(attempts))*100:.1f}%)")
        
        print("\nItérations et opcodes médians / moyens par motif :")
        for r in reasons:
            sub = [a for a in attempts if a["reason"] == r]
            its = [a["iters"] for a in sub]
            ops = [a["ops"] for a in sub]
            med_it = statistics.median(its)
            mean_it = statistics.mean(its)
            med_ops = statistics.median(ops)
            mean_ops = statistics.mean(ops)
            print(f"  {r:<10} (n={len(sub):2d}): iters med={med_it:5.0f} (mean={mean_it:5.0f}) | ops med={med_ops/1e6:5.2f}M (mean={mean_ops/1e6:5.2f}M)")

    # AAA HogEx
    print("\n" + "=" * 80)
    print("--- AAAHOGEX : TENTATIVES ROUTEBUILDER RAILROUTE ---")
    print("=" * 80)
    for arm in ["reference", "v299"]:
        routes = data["aaa_routes"][arm]
        succ = sum(1 for r in routes if r["status"] == "Succeeded")
        print(f"\nAAA face à {arm} (N={len(routes)}) - Succès: {succ}/{len(routes)} ({succ/max(1, len(routes))*100:.1f}%)")
        causes = sorted(list(set(r["cause"] for r in routes)))
        header = f"{'Statut / Motif':<26}" + "".join([f"{label:>10}" for label, _, _ in SLICES]) + f"{'Total':>10}"
        print(header)
        print("-" * len(header))
        for c in causes:
            row = f"{c:<26}"
            tot_c = 0
            for label, _, _ in SLICES:
                cnt = sum(1 for r in routes if r["cause"] == c and r["slice"] == label)
                tot_c += cnt
                row += f"{cnt:>10}"
            row += f"{tot_c:>10}"
            print(row)
        print("-" * len(header))
        tot_row = f"{'TOTAL':<26}"
        for label, _, _ in SLICES:
            cnt = sum(1 for r in routes if r["slice"] == label)
            tot_row += f"{cnt:>10}"
        tot_row += f"{len(routes):>10}"
        print(tot_row)
        
        print("\nJours médians par motif AAA :")
        for c in causes:
            c_days = [r["days"] for r in routes if r["cause"] == c]
            med_d = statistics.median(c_days) if c_days else 0
            print(f"  {c:<26} (n={len(c_days):2d}): jours med={med_d:4.0f} [min={min(c_days)}, max={max(c_days)}]")

    # AAA Path Found stats
    print("\n--- AAAHOGEX : APPELS ET ITERATIONS LORSQUE LE CHEMIN EST TROUVE ---")
    for arm in ["reference", "v299"]:
        paths = data["aaa_paths"][arm]
        print(f"\nAAA face à {arm} (N={len(paths)} chemins trouvés) :")
        for label, _, _ in SLICES:
            sub = [p for p in paths if p["slice"] == label]
            if sub:
                med_calls = statistics.median([p["count"] for p in sub])
                med_iters = statistics.median([p["iters"] for p in sub])
                med_days = statistics.median([p["days"] for p in sub])
                print(f"  {label:<10} (n={len(sub):2d}): appels med={med_calls:4.1f} (~{med_iters:5.0f} iters) | jours med={med_days:4.1f}")

    # ABND < 100 tiles inventory
    print("\n" + "=" * 80)
    print("--- INVENTAIRE DES ABND A < 100 TUILES MANHATTAN ---")
    print("=" * 80)
    ref_abnd_under_100 = [a for a in data["opex"]["reference"] if a["reason"] == "ABND" and a["manh"] < 100]
    v299_abnd_under_100 = [a for a in data["opex"]["v299"] if a["reason"] == "ABND" and a["manh"] < 100]
    
    print(f"\nTotal ABND < 100 dans master (reference) : {len(ref_abnd_under_100)}")
    print(f"Total ABND < 100 dans v299 (adapt=400)   : {len(v299_abnd_under_100)}")
    
    print("\nDétail des 22 ABND < 100 dans reference (master) :")
    for idx, a in enumerate(ref_abnd_under_100, 1):
        print(f"  {idx:2d}. s{a['seed']:3d} {a['date']} manh={a['manh']:2d} src={a['src']:5d} {a['src_coord']} -> dst={a['dst']:5d} {a['dst_coord']} "
              f"kind={a['kind']:<7s} profit={a['pred_profit']:6d}£ roi={a['pred_roi']:4d} ops={a['ops']/1e6:4.1f}M weight={a['weight']}")

    print("\nDétail des 2 ABND < 100 dans v299 :")
    for idx, a in enumerate(v299_abnd_under_100, 1):
        print(f"  {idx:2d}. s{a['seed']:3d} {a['date']} manh={a['manh']:2d} src={a['src']:5d} {a['src_coord']} -> dst={a['dst']:5d} {a['dst_coord']} "
              f"kind={a['kind']:<7s} profit={a['pred_profit']:6d}£ roi={a['pred_roi']:4d} ops={a['ops']/1e6:4.1f}M adapt={a['adapt']}")

    # Cross check of reference ABNDs in v299
    print("\n--- DEVENIR DANS V299 DES PAIRES AYANT ABND DANS REFERENCE ---")
    unique_ref_pairs = set((a["seed"], a["src"], a["dst"]) for a in ref_abnd_under_100)
    for seed, src, dst in sorted(unique_ref_pairs):
        matches = [a for a in data["opex"]["v299"] if a["seed"] == seed and a["src"] == src and a["dst"] == dst]
        if matches:
            for m in matches:
                print(f"  s{seed:3d} ({src}, {dst}) : ok={m['ok']} reason={m['reason']} iters={m['iters']} adapt={m['adapt']} ops={m['ops']/1e6:.2f}M")
        else:
            print(f"  s{seed:3d} ({src}, {dst}) : NON TENTE dans v299")

def main():
    log_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    data = parse_logs(log_dir)
    print_report(data)

if __name__ == "__main__":
    main()
