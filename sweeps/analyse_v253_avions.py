#!/usr/bin/env python3
"""
Diagnostic V253 : Analyse causale et comparative du choix d'avion
(OpexAI vs AAAHogEx, V252 mode 2 vs reference).
"""

import json
import os
import re
import glob
from collections import defaultdict

BASE_DIR = "/home/deploy/projects/openttd-ml/results"
JSON_AIRSEUL = os.path.join(BASE_DIR, "v252m2_airseul_20x10_20261018.json")
ENGINE_DIR = os.path.join(BASE_DIR, "v252m2_airseul_20x10_20261018_engine")

ENGINES = {
    215: {"name": "Sampson U52", "intro": 1928, "speed_disp": 473, "speed_noai": 118, "pax": 25, "mail": 4, "price": 28710, "running": 2390, "type": "small"},
    216: {"name": "Coleman Count", "intro": 1947, "speed_disp": 473, "speed_noai": 118, "pax": 65, "mail": 8, "price": 30761, "running": 2812, "type": "small"},
    217: {"name": "FFP Dart", "intro": 1954, "speed_disp": 947, "speed_noai": 236, "pax": 90, "mail": 10, "price": 32812, "running": 3656, "type": "small"},
    218: {"name": "Yate Haugan", "intro": 1968, "speed_disp": 2316, "speed_noai": 579, "pax": 100, "mail": 20, "price": 153808, "running": 7031, "type": "big"},
    219: {"name": "Bakewell Cotswald LB-3", "intro": 1933, "speed_disp": 473, "speed_noai": 118, "pax": 30, "mail": 6, "price": 30761, "running": 2756, "type": "small"},
    220: {"name": "Bakewell Luckett LB-8", "intro": 1957, "speed_disp": 947, "speed_noai": 236, "pax": 200, "mail": 30, "price": 36914, "running": 6750, "type": "big"},
    221: {"name": "Bakewell Luckett LB-9", "intro": 1964, "speed_disp": 947, "speed_noai": 236, "pax": 100, "mail": 15, "price": 34863, "running": 4218, "type": "small"},
    222: {"name": "Bakewell Luckett LB80", "intro": 1978, "speed_disp": 947, "speed_noai": 236, "pax": 150, "mail": 30, "price": 36914, "running": 6890, "type": "big"},
    223: {"name": "Bakewell Luckett LB-10", "intro": 1970, "speed_disp": 947, "speed_noai": 236, "pax": 220, "mail": 40, "price": 38964, "running": 5400, "type": "big"},
    224: {"name": "Bakewell Luckett LB-11", "intro": 1989, "speed_disp": 947, "speed_noai": 236, "pax": 230, "mail": 25, "price": 41015, "running": 5343, "type": "big"},
    225: {"name": "Yate Aerospace YAC 1-11", "intro": 1962, "speed_disp": 947, "speed_noai": 236, "pax": 95, "mail": 10, "price": 32812, "running": 3796, "type": "small"},
    226: {"name": "Darwin 100", "intro": 1962, "speed_disp": 947, "speed_noai": 236, "pax": 170, "mail": 35, "price": 36914, "running": 6750, "type": "big"},
    227: {"name": "Darwin 200", "intro": 1966, "speed_disp": 947, "speed_noai": 236, "pax": 110, "mail": 15, "price": 34863, "running": 4359, "type": "small"},
    228: {"name": "Darwin 300", "intro": 1967, "speed_disp": 947, "speed_noai": 236, "pax": 300, "mail": 50, "price": 61523, "running": 7115, "type": "big"},
    232: {"name": "Guru Galaxy", "intro": 1969, "speed_disp": 947, "speed_noai": 236, "pax": 240, "mail": 35, "price": 51269, "running": 6328, "type": "big"},
    233: {"name": "Airtaxi A21", "intro": 1972, "speed_disp": 947, "speed_noai": 236, "pax": 260, "mail": 30, "price": 41015, "running": 6609, "type": "big"},
}

def identify_engine(pax_cap, mail_cap):
    if pax_cap == 0 and mail_cap > 0:
        # Refit to mail pure!
        # Find which aircraft has this mail capacity when refitted
        # In OpenTTD, refit mail capacity is often 1.5x or 2x pax cap, or mail_cap
        for eid, info in ENGINES.items():
            if info["mail"] * 2 == mail_cap or info["pax"] == mail_cap or info["mail"] == mail_cap:
                return eid
    for eid, info in ENGINES.items():
        if info["pax"] == pax_cap and info["mail"] == mail_cap:
            return eid
    for eid, info in ENGINES.items():
        if info["pax"] == pax_cap:
            return eid
    return None

def manhattan_dist(t1, t2):
    x1, y1 = t1 % 512, t1 // 512
    x2, y2 = t2 % 512, t2 // 512
    return abs(x1 - x2) + abs(y1 - y2)

def parse_kv(line):
    kv = {}
    for part in line.split():
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k] = v
    return kv

def analyze_logs():
    print("=== Analyse des journaux moteurs v252m2 (20 graines) ===")
    log_files = glob.glob(os.path.join(ENGINE_DIR, "v252m2_seed*_r0.log"))
    print(f"Fichiers logs trouvés: {len(log_files)}")
    
    c121_builds = []
    v252_replaces = []
    v252_skips = defaultdict(int)
    aaa_choices = []
    
    aaa_choice_re = re.compile(r"ChooseEngine:([A-Za-z0-9\- ]+?) (?:old:[A-Za-z0-9\- ]+? )?production:(\d+) (.*?)$")
    
    for lf in sorted(log_files):
        seed_match = re.search(r"seed(\d+)", lf)
        seed = int(seed_match.group(1)) if seed_match else 0
        with open(lf, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "C121_BUILD" in line:
                    kv = parse_kv(line)
                    c121_builds.append({
                        "seed": seed,
                        "line": int(kv.get("line", -1)),
                        "engine": int(kv.get("engine", -1)),
                        "pax_cap": int(kv.get("pax_cap", 0)),
                        "mail_cap": int(kv.get("mail_cap", 0)),
                        "actual_profit": int(float(kv.get("actual_profit", 0))),
                        "decision_profit": int(float(kv.get("decision_profit", 0))),
                        "target_profit": int(float(kv.get("target_profit", 0))),
                        "actual_n": int(kv.get("actual_n", 1)),
                        "target_n": int(kv.get("target_n", 1)),
                        "dist": int(kv.get("payment_distance", 0)),
                        "raw": line.strip()
                    })
                elif "V252_REPLACE" in line:
                    kv = parse_kv(line)
                    v252_replaces.append({
                        "seed": seed,
                        "line": int(kv.get("line", -1)),
                        "old_engine": int(kv.get("old_engine", -1)),
                        "new_engine": int(kv.get("new_engine", -1)),
                        "price": int(kv.get("price", 0)),
                        "age": int(kv.get("age", 0)),
                        "profit": int(float(kv.get("profit", 0))),
                        "raw": line.strip()
                    })
                elif "V252_SKIP" in line:
                    kv = parse_kv(line)
                    reason = kv.get("reason", "unknown")
                    v252_skips[reason] += 1
                elif "ChooseEngine:" in line:
                    m = aaa_choice_re.search(line)
                    if m:
                        aaa_choices.append({
                            "seed": seed,
                            "engine_name": m.group(1).strip(),
                            "production": int(m.group(2)),
                            "route": m.group(3).strip()
                        })

    print(f"C121_BUILD events: {len(c121_builds)}")
    print(f"V252_REPLACE events: {len(v252_replaces)}")
    print(f"V252_SKIP breakdown: {dict(v252_skips)}")
    print(f"AAAHogEx ChooseEngine events: {len(aaa_choices)}")
    
    # Engine breakdown in C121_BUILD
    c121_engines = defaultdict(int)
    c121_pred_profit = defaultdict(list)
    c121_dist = defaultdict(list)
    for b in c121_builds:
        c121_engines[b["engine"]] += 1
        c121_pred_profit[b["engine"]].append(b["decision_profit"] / max(1, b["actual_n"]))
        c121_dist[b["engine"]].append(b["dist"])
    print("\n--- OpexAI: Moteurs choisis à l'ouverture de ligne (C121_BUILD) ---")
    for eng, count in sorted(c121_engines.items(), key=lambda x: -x[1]):
        name = ENGINES.get(eng, {}).get("name", f"Unknown {eng}")
        avg_pred = sum(c121_pred_profit[eng]) / len(c121_pred_profit[eng])
        avg_dist = sum(c121_dist[eng]) / len(c121_dist[eng])
        print(f"Engine {eng} ({name}): {count} ouvertures ({count/len(log_files):.1f}/graine), profit prédit unitaire: {avg_pred:.0f} £/an, dist moy: {avg_dist:.0f}")

    # Engine breakdown in V252_REPLACE
    rep_from_to = defaultdict(int)
    rep_new_engine = defaultdict(int)
    rep_profits = defaultdict(list)
    for r in v252_replaces:
        rep_from_to[(r["old_engine"], r["new_engine"])] += 1
        rep_new_engine[r["new_engine"]] += 1
        rep_profits[r["new_engine"]].append(r["profit"])
    print("\n--- OpexAI: Moteurs choisis lors du remplacement actif (V252_REPLACE) ---")
    for eng, count in sorted(rep_new_engine.items(), key=lambda x: -x[1]):
        name = ENGINES.get(eng, {}).get("name", f"Unknown {eng}")
        pct = count / len(v252_replaces) * 100
        avg_prof = sum(rep_profits[eng]) / len(rep_profits[eng])
        print(f"Engine {eng:3d} ({name:23s}): {count:3d} remplacements ({count/len(log_files):4.1f}/graine, {pct:4.1f}%), profit ligne avant rempl.: {avg_prof:6.0f} £")

    return c121_builds, v252_replaces

def analyze_telemetry():
    print("\n=== Analyse de la télémétrie des lignes (v252m2_airseul_20x10_20261018.json) ===")
    with open(JSON_AIRSEUL, "r") as f:
        data = json.load(f)
    
    snapshots = data["line_telemetry"]["snapshots"]
    print(f"Total snapshots: {len(snapshots)}")
    
    fleet_by_year = {
        "OpexAI": defaultdict(lambda: defaultdict(list)),
        "AAAHogEx": defaultdict(lambda: defaultdict(list))
    }
    
    adequacy_data = defaultdict(list)
    
    aaa_airport_engines = defaultdict(lambda: defaultdict(set))
    opex_airport_engines = defaultdict(lambda: defaultdict(set))
    
    for s in snapshots:
        arm = s["arm"]
        seed = s["seed"]
        year = s["year"]
        lines = s.get("lines", [])
        
        for l in lines:
            if l.get("mode") != "air":
                continue
            vehs = l.get("vehicles", 0)
            if vehs <= 0:
                continue
            caps = l.get("capacity_by_cargo", {})
            pax_cap = caps.get("0", 0) // vehs
            mail_cap = caps.get("2", 0) // vehs
            
            eid = identify_engine(pax_cap, mail_cap)
            
            tiles = l.get("ordered_station_tiles", [])
            dist = 0
            if len(tiles) >= 2:
                dist = manhattan_dist(tiles[0], tiles[1])
            
            fin = l.get("vehicle_financials", [])
            profit_this_year = l.get("profit_this_year_gbp", 0.0)
            profit_last_year = l.get("profit_last_year_gbp", 0.0)
            
            stats = l.get("endpoint_cargo_stats", [])
            ratings = []
            waitings = []
            for st in stats:
                cstats = st.get("cargo", {})
                if "0" in cstats:
                    r = cstats["0"].get("rating")
                    if r is not None and r >= 0:
                        ratings.append(r)
                    w = cstats["0"].get("max_waiting_cargo")
                    if w is not None and w >= 0:
                        waitings.append(w)
                ap_tile = st.get("tile")
                if ap_tile is not None and eid is not None:
                    if arm == "AAAHogEx":
                        aaa_airport_engines[seed][ap_tile].add(eid)
                    else:
                        opex_airport_engines[seed][ap_tile].add(eid)
            
            avg_rating = sum(ratings)/len(ratings) if ratings else None
            max_waiting = max(waitings) if waitings else None
            
            for v in fin:
                fleet_by_year[arm][year][eid].append(v)
                
            adequacy_data[eid].append({
                "arm": arm,
                "year": year,
                "seed": seed,
                "distance": dist,
                "pax_cap": pax_cap,
                "mail_cap": mail_cap,
                "vehs": vehs,
                "profit_this_year": profit_this_year / vehs if vehs > 0 else 0,
                "profit_last_year": profit_last_year / vehs if vehs > 0 else 0,
                "rating": avg_rating,
                "max_waiting": max_waiting
            })

    print("\n--- Flotte OpexAI par modèle et par an (moyenne d'avions par graine) ---")
    years = sorted(list(fleet_by_year["OpexAI"].keys()))
    for y in [1971, 1973, 1975, 1977, 1979]:
        if y not in fleet_by_year["OpexAI"]: continue
        print(f"\nAnnée {y}:")
        total_v = sum(len(vlist) for vlist in fleet_by_year["OpexAI"][y].values()) / 20.0
        for eid, vlist in sorted(fleet_by_year["OpexAI"][y].items(), key=lambda x: -len(x[1])):
            cnt = len(vlist) / 20.0
            pct = cnt / total_v * 100 if total_v > 0 else 0
            eid_str = f"ID {eid:3d}" if eid is not None else "ID Unk"
            name = ENGINES.get(eid, {}).get("name", f"Unknown {eid}")
            last_profits = [v["profit_last_year_gbp"] for v in vlist if v.get("profit_last_year_gbp", 0) > 0]
            avg_last = sum(last_profits)/len(last_profits) if last_profits else 0
            this_profits = [v["profit_this_year_gbp"] for v in vlist]
            avg_this = (sum(this_profits)/len(this_profits) * 12 / 11) if this_profits else 0
            print(f"  {eid_str} ({name:23s}): {cnt:5.1f} av ({pct:4.1f}%) | Prof. mature: {avg_last:6.0f} £ | Prof. an 12/11: {avg_this:6.0f} £")

    print("\n--- Flotte AAAHogEx par modèle et par an (moyenne d'avions par graine) ---")
    for y in [1971, 1975, 1979]:
        if y not in fleet_by_year["AAAHogEx"]: continue
        print(f"\nAnnée {y}:")
        total_v = sum(len(vlist) for vlist in fleet_by_year["AAAHogEx"][y].values()) / 20.0
        for eid, vlist in sorted(fleet_by_year["AAAHogEx"][y].items(), key=lambda x: -len(x[1])):
            cnt = len(vlist) / 20.0
            pct = cnt / total_v * 100 if total_v > 0 else 0
            eid_str = f"ID {eid:3d}" if eid is not None else "ID Unk"
            name = ENGINES.get(eid, {}).get("name", f"Unknown {eid}")
            last_profits = [v["profit_last_year_gbp"] for v in vlist if v.get("profit_last_year_gbp", 0) > 0]
            avg_last = sum(last_profits)/len(last_profits) if last_profits else 0
            this_profits = [v["profit_this_year_gbp"] for v in vlist]
            avg_this = (sum(this_profits)/len(this_profits) * 12 / 11) if this_profits else 0
            print(f"  {eid_str} ({name:23s}): {cnt:5.1f} av ({pct:4.1f}%) | Prof. mature: {avg_last:6.0f} £ | Prof. an 12/11: {avg_this:6.0f} £")

    # Adequacy by distance brackets
    print("\n--- Adéquation : Profit réalisé par tranche de distance Manhattan (1975-1979) ---")
    dist_brackets = [(0, 128), (128, 160), (160, 192), (192, 999)]
    for b_min, b_max in dist_brackets:
        label = f"Distance [{b_min}, {b_max})"
        print(f"\n{label}:")
        for eid in [217, 218, 221, 223, 226, 227, 228]:
            items = [it for it in adequacy_data[eid] if b_min <= it["distance"] < b_max and it["year"] >= 1975]
            if not items: continue
            opex_items = [it for it in items if it["arm"] == "OpexAI"]
            aaa_items = [it for it in items if it["arm"] == "AAAHogEx"]
            name = ENGINES.get(eid, {}).get("name", str(eid))
            
            res_str = f"  ID {eid:3d} ({name:20s}):"
            if opex_items:
                p_op = sum(it["profit_this_year"] * 12/11 for it in opex_items)/len(opex_items)
                rats = [it["rating"] for it in opex_items if it["rating"] is not None]
                r_op = sum(rats)/len(rats) if rats else 0
                waits = [it["max_waiting"] for it in opex_items if it["max_waiting"] is not None]
                w_op = sum(waits)/len(waits) if waits else 0
                res_str += f" OPEX n={len(opex_items):3d} p={p_op:6.0f}£ r={r_op:.1f} w={w_op:4.0f} |"
            if aaa_items:
                p_aaa = sum(it["profit_this_year"] * 12/11 for it in aaa_items)/len(aaa_items)
                rats = [it["rating"] for it in aaa_items if it["rating"] is not None]
                r_aaa = sum(rats)/len(rats) if rats else 0
                waits = [it["max_waiting"] for it in aaa_items if it["max_waiting"] is not None]
                w_aaa = sum(waits)/len(waits) if waits else 0
                res_str += f" AAA n={len(aaa_items):3d} p={p_aaa:6.0f}£ r={r_aaa:.1f} w={w_aaa:4.0f}"
            print(res_str)

    # AAA Airport model mixing
    print("\n--- Mélange des modèles d'avion sur un même aéroport (1979) ---")
    aaa_mixed_airports = 0
    aaa_total_airports = 0
    aaa_models_per_ap = []
    for seed, aps in aaa_airport_engines.items():
        for ap, engs in aps.items():
            aaa_total_airports += 1
            aaa_models_per_ap.append(len(engs))
            if len(engs) > 1:
                aaa_mixed_airports += 1
    
    opex_mixed_airports = 0
    opex_total_airports = 0
    opex_models_per_ap = []
    for seed, aps in opex_airport_engines.items():
        for ap, engs in aps.items():
            opex_total_airports += 1
            opex_models_per_ap.append(len(engs))
            if len(engs) > 1:
                opex_mixed_airports += 1

    print(f"AAAHogEx: {aaa_total_airports} aéroports observés, {aaa_mixed_airports} avec 2+ modèles différents ({aaa_mixed_airports/aaa_total_airports*100:.1f}%), max modèles/aéroport: {max(aaa_models_per_ap) if aaa_models_per_ap else 0}")
    print(f"OpexAI:   {opex_total_airports} aéroports observés, {opex_mixed_airports} avec 2+ modèles différents ({opex_mixed_airports/opex_total_airports*100:.1f}%), max modèles/aéroport: {max(opex_models_per_ap) if opex_models_per_ap else 0}")

    return fleet_by_year, adequacy_data

if __name__ == "__main__":
    analyze_logs()
    analyze_telemetry()
