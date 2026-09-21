"""Banc Year 1 (1970) sur 5 graines :
- Baseline : air_full_load=0, feeder_hub_check=0
- FullLoad_Blind : air_full_load=1, feeder_hub_check=0
- Smart_Feeders : air_full_load=0, feeder_hub_check=1
- FullLoad_Smart : air_full_load=1, feeder_hub_check=1 (demande utilisateur)
"""
import statistics
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import make_cfg, year_profit, quarter_profit, station_ratings

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}
VEHICLE_MODES = ("train", "roadveh", "ship", "aircraft")

def _first(value):
    return value[0] if isinstance(value, list) and value else value

def vehicle_breakdown(chunks, owner=0):
    counts = {mode: 0 for mode in VEHICLE_MODES}
    for vehicle in (chunks.get("VEHS") or {}).values():
        if not isinstance(vehicle, dict): continue
        vtype = str(vehicle.get("type"))
        if vtype not in TYPE_TO_MODE: continue
        mode = TYPE_TO_MODE[vtype]
        body = _first(vehicle.get(mode))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner: continue
        if not common.get("unitnumber"): continue
        counts[mode] += 1
    return counts

def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    ratings = station_ratings(chunks)
    counts = vehicle_breakdown(chunks)

    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "company_value": last.get("company_value", 0),
        "profit_year": year_profit(closed) or 0,
        "performance_history": last.get("performance_history", 0),
        "delivered_cargo": last.get("delivered_cargo", 0),
        "money": player.get("money", 0),
        "current_loan": player.get("current_loan", 0),
        "n_vehicles": sum(counts.values()),
        "by_mode": counts,
        "n_stations": len(chunks.get("STNN") or {}),
    },)

def main():
    cfg = make_cfg(1970)
    seeds = [42, 100, 7, 999, 2026]
    experiments = []

    arms = {
        "Baseline": (("air_full_load", 0), ("feeder_hub_check", 0)),
        "FullLoad_Blind": (("air_full_load", 1), ("feeder_hub_check", 0)),
        "Smart_Feeders": (("air_full_load", 0), ("feeder_hub_check", 1)),
        "FullLoad_Smart": (("air_full_load", 1), ("feeder_hub_check", 1)),
    }

    ai_arms = {
        name: local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", params)
        for name, params in arms.items()
    }

    for s in seeds:
        for arm_name, ai_obj in ai_arms.items():
            experiments.append({
                "bench_arm": arm_name,
                "seed": s,
                "days": 365,
                "openttd_config": cfg,
                "ais": (ai_obj,),
            })

    print(f"Lancement banc 4 bras x 5 graines Annee 1 (20 runs)...")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=8,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    by_run = {}
    for r in rows:
        if r["date"].startswith("1970-12") or r["date"].startswith("1971-01"):
            by_run[(r["arm"], r["seed"])] = r

    arm_order = ["Baseline", "FullLoad_Blind", "Smart_Feeders", "FullLoad_Smart"]

    print("\n" + "=" * 125)
    print("BANC ANNEE 1 (1970) : AIR FULL LOAD & FEEDERS INTELLIGENTS (5 GRAINES)")
    print("=" * 125)

    print("\n--- 1. COMPARAISON DIRECTE PAR GRAINE : VALEUR DE LA COMPAGNIE (£) ---")
    hdr = f"{'Graine':<7} | {'Baseline':<12} | {'FullLoad_Blind':<16} | {'Smart_Feeders':<16} | {'FullLoad_Smart':<16} | {'Gain Combined vs Base':<20}"
    print(hdr)
    print("-" * len(hdr))
    for s in seeds:
        v_base = by_run.get(("Baseline", s), {}).get("company_value", 0)
        v_flb = by_run.get(("FullLoad_Blind", s), {}).get("company_value", 0)
        v_sm = by_run.get(("Smart_Feeders", s), {}).get("company_value", 0)
        v_comb = by_run.get(("FullLoad_Smart", s), {}).get("company_value", 0)
        diff = ((v_comb - v_base) / v_base * 100) if v_base > 0 else 0
        print(f"{s:<7} | {v_base:>12,.0f} | {v_flb:>16,.0f} | {v_sm:>16,.0f} | {v_comb:>16,.0f} | {diff:>+18.1f}%")

    print("-" * len(hdr))
    for name, fn in [("MOYENNE", statistics.mean), ("MEDIANE", statistics.median)]:
        m_base = fn([by_run.get(("Baseline", s), {}).get("company_value", 0) for s in seeds])
        m_flb = fn([by_run.get(("FullLoad_Blind", s), {}).get("company_value", 0) for s in seeds])
        m_sm = fn([by_run.get(("Smart_Feeders", s), {}).get("company_value", 0) for s in seeds])
        m_comb = fn([by_run.get(("FullLoad_Smart", s), {}).get("company_value", 0) for s in seeds])
        diff = ((m_comb - m_base) / m_base * 100) if m_base > 0 else 0
        print(f"{name:<7} | {m_base:>12,.0f} | {m_flb:>16,.0f} | {m_sm:>16,.0f} | {m_comb:>16,.0f} | {diff:>+18.1f}%")

    print("\n--- 2. COMPARAISON DU PROFIT ANNUEL (£) ---")
    hdr_p = f"{'Graine':<7} | {'Baseline':<12} | {'FullLoad_Blind':<16} | {'Smart_Feeders':<16} | {'FullLoad_Smart':<16} | {'Gain Combined vs Base':<20}"
    print(hdr_p)
    print("-" * len(hdr_p))
    for s in seeds:
        p_base = by_run.get(("Baseline", s), {}).get("profit_year", 0)
        p_flb = by_run.get(("FullLoad_Blind", s), {}).get("profit_year", 0)
        p_sm = by_run.get(("Smart_Feeders", s), {}).get("profit_year", 0)
        p_comb = by_run.get(("FullLoad_Smart", s), {}).get("profit_year", 0)
        diff = ((p_comb - p_base) / p_base * 100) if p_base > 0 else 0
        print(f"{s:<7} | {p_base:>12,.0f} | {p_flb:>16,.0f} | {p_sm:>16,.0f} | {p_comb:>16,.0f} | {diff:>+18.1f}%")

    print("-" * len(hdr_p))
    for name, fn in [("MOYENNE", statistics.mean), ("MEDIANE", statistics.median)]:
        m_base = fn([by_run.get(("Baseline", s), {}).get("profit_year", 0) for s in seeds])
        m_flb = fn([by_run.get(("FullLoad_Blind", s), {}).get("profit_year", 0) for s in seeds])
        m_sm = fn([by_run.get(("Smart_Feeders", s), {}).get("profit_year", 0) for s in seeds])
        m_comb = fn([by_run.get(("FullLoad_Smart", s), {}).get("profit_year", 0) for s in seeds])
        diff = ((m_comb - m_base) / m_base * 100) if m_base > 0 else 0
        print(f"{name:<7} | {m_base:>12,.0f} | {m_flb:>16,.0f} | {m_sm:>16,.0f} | {m_comb:>16,.0f} | {diff:>+18.1f}%")

    print("\n--- 3. RECAPITULATIF MOYEN PAR BRAS (1970) ---")
    hdr_tot = f"{'Arm':<16} | {'Valeur Moy':<12} | {'Profit Moy':<12} | {'Score Moy':<10} | {'Avions':<8} | {'Bus/Camions':<12} | {'Cash Final':<12}"
    print(hdr_tot)
    print("-" * len(hdr_tot))
    for arm in arm_order:
        vals = [by_run.get((arm, s), {}).get("company_value", 0) for s in seeds]
        profs = [by_run.get((arm, s), {}).get("profit_year", 0) for s in seeds]
        scs = [by_run.get((arm, s), {}).get("performance_history", 0) for s in seeds]
        planes = [by_run.get((arm, s), {}).get("by_mode", {}).get("aircraft", 0) for s in seeds]
        roads = [by_run.get((arm, s), {}).get("by_mode", {}).get("roadveh", 0) for s in seeds]
        cash = [by_run.get((arm, s), {}).get("money", 0) for s in seeds]
        print(f"{arm:<16} | {statistics.mean(vals):>12,.0f} | {statistics.mean(profs):>12,.0f} | {statistics.mean(scs):>10.1f} | {statistics.mean(planes):>8.1f} | {statistics.mean(roads):>12.1f} | {statistics.mean(cash):>12,.0f}")

if __name__ == "__main__":
    main()
