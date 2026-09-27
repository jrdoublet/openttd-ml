#!/usr/bin/env python3
import json
import statistics
from collections import Counter, defaultdict

with open('results/v88inv_probed_summary.json') as f:
    d = json.load(f)

print("=====================================================================")
print("ANALYSE DÉTAILLÉE DES 5 PISTES PAR LA MESURE (SEEDS 100, 999, 5678)")
print("=====================================================================\n")

# 1. PISTE 1 : ARRÊTS DE PASSE (C78 pass_stop)
print("--- PISTE 1 : ARRÊTS DE PASSE ---")
for r in d['results']:
    arm = r['arm']
    seed = r['seed']
    analysis = r['analysis']
    short_arm = 'Ref' if 'v88_goods_chain=0' in arm else ('ChainOnly' if 'v88_all_inputs' not in arm else 'Unlocked')
    stops = analysis['c78_pass_stops']
    total_stops = len(stops)
    reasons = Counter()
    for ps in stops:
        reasons[ps.get('reason')] += 1
    pct_rail = (reasons['rail_search'] / total_stops * 100) if total_stops else 0
    pct_kpass = (reasons['k_pass'] / total_stops * 100) if total_stops else 0
    pct_cash = (reasons['cash'] / total_stops * 100) if total_stops else 0
    print(f"{short_arm:10} seed={seed:4}: total_stops={total_stops:3} | cash={reasons['cash']:3} ({pct_cash:4.1f}%) | k_pass={reasons['k_pass']:2} ({pct_kpass:4.1f}%) | rail_search={reasons['rail_search']:2} ({pct_rail:4.1f}%)")

# 2. PISTE 3 : CAPITAL ET DÉPENSES PAR MODE
print("\n--- PISTE 3 : CAPITAL ET DÉPENSES PAR MODE ---")
for r in d['results']:
    arm = r['arm']
    seed = r['seed']
    analysis = r['analysis']
    short_arm = 'Ref' if 'v88_goods_chain=0' in arm else ('ChainOnly' if 'v88_all_inputs' not in arm else 'Unlocked')
    spends = analysis['spend_by_year_mode']
    total_air = sum(spends.get(str(yr), {}).get('air', 0) + spends.get(yr, {}).get('air', 0) for yr in range(1970, 1976))
    total_rail = sum(spends.get(str(yr), {}).get('rail', 0) + spends.get(yr, {}).get('rail', 0) for yr in range(1970, 1976))
    total_fleet = sum(spends.get(str(yr), {}).get('fleet', 0) + spends.get(yr, {}).get('fleet', 0) for yr in range(1970, 1976))
    total_road = sum(spends.get(str(yr), {}).get('road', 0) + spends.get(yr, {}).get('road', 0) for yr in range(1970, 1976))
    print(f"{short_arm:10} seed={seed:4}: Total Spend: Air={total_air:8} £ | Rail={total_rail:7} £ | Fleet={total_fleet:7} £ | Road={total_road:6} £")

# 3. PISTE 4 : OPCODES / TEMPS / CADENCE DES PASSES
print("\n--- PISTE 4 : CADENCE DES PASSES ET JOURS ENTRE PASSES ---")
for r in d['results']:
    arm = r['arm']
    seed = r['seed']
    analysis = r['analysis']
    short_arm = 'Ref' if 'v88_goods_chain=0' in arm else ('ChainOnly' if 'v88_all_inputs' not in arm else 'Unlocked')
    passes = analysis['c78_projects_pass']
    n_passes = len(passes)
    # Calcul des intervalles de temps (en jours) entre passes successives
    intervals = []
    # Dates des passes
    import datetime
    def parse_dt(s):
        parts = s.split('-')
        return int(parts[0]) * 365 + int(parts[1]) * 30 + int(parts[2])
    
    for i in range(1, len(passes)):
        d1 = parse_dt(passes[i-1]['date'])
        d2 = parse_dt(passes[i]['date'])
        intervals.append(d2 - d1)
    
    med_int = statistics.median(intervals) if intervals else None
    max_int = max(intervals) if intervals else None
    print(f"{short_arm:10} seed={seed:4}: Total passes={n_passes:3} | Intervalle médian={med_int} j | Max={max_int} j")

# 4. PISTE 2 & 5 : DÉTAIL DES CONSTRUCTIONS ET ÉVOLUTION DES FLOTTES
print("\n--- DÉTAIL DES CONSTRUCTIONS ET ÉVOLUTION DES FLOTTES ---")
for r in d['results']:
    arm = r['arm']
    seed = r['seed']
    analysis = r['analysis']
    short_arm = 'Ref' if 'v88_goods_chain=0' in arm else ('ChainOnly' if 'v88_all_inputs' not in arm else 'Unlocked')
    # Builds list
    builds_by_mode = Counter(b.get('mode') for b in analysis['c50_builds'])
    fl_air = sum(fb.get('added', 0) for fb in analysis['c50_fleet_builds'] if fb.get('mode') == 'air')
    vehs = r.get('primary_vehicles_by_mode', {})
    print(f"{short_arm:10} seed={seed:4}: Lignes bâties={dict(builds_by_mode)} | Avions flotte ajoutés={fl_air} | Flotte finale: Air={vehs.get('air', 0)} Rail={vehs.get('rail', 0)}")
