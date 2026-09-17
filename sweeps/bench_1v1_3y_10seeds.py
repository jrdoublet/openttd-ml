"""Banc comparatif 1v1 OpexAI vs AAAHogEx : 10 graines x 3 ans.

Compare les chiffres principaux annee par annee (Annees 1 a 3, 1970 a 1972) :
- Valeur d'entreprise (Company Value)
- Profit annuel (Profit Year)
- Score officiel de performance (Performance History)
- Nombre de vehicules (total et mix train / route / avion / bateau)
- Nombre de gares / stations
- Tresorerie (money) et emprunt (current_loan)
- Note de gare mediane
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit, station_ratings
from physical_counters import decode_vehicles

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026, 1, 17, 73, 314, 512)
DEFAULT_YEARS = 3
STARTING_YEAR = 1970
VEHICLE_MODES = ("train", "roadveh", "ship", "aircraft")
TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def vehicle_breakdown(chunks, owner=0):
    counts = {mode: 0 for mode in VEHICLE_MODES}
    profit_by_mode = {mode: 0 for mode in VEHICLE_MODES}
    capital_by_mode = {mode: 0 for mode in VEHICLE_MODES}
    profits = []
    capital = 0
    capacity = 0
    for vehicle in (chunks.get("VEHS") or {}).values():
        if not isinstance(vehicle, dict):
            continue
        vtype = str(vehicle.get("type"))
        if vtype not in TYPE_TO_MODE:
            continue
        mode = TYPE_TO_MODE[vtype]
        body = _first(vehicle.get(mode))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict):
            continue
        if common.get("owner") != owner:
            continue
        if not common.get("unitnumber"):
            capacity += common.get("cargo_cap") or 0
            val = common.get("value") or 0
            capital += val
            capital_by_mode[mode] += val
            continue
        counts[mode] += 1
        value = common.get("value") or 0
        capital += value
        capital_by_mode[mode] += value
        capacity += common.get("cargo_cap") or 0
        profit = common.get("profit_this_year")
        if profit is not None:
            profits.append(profit)
            profit_by_mode[mode] += profit
    return {
        "by_mode": counts,
        "n_units": sum(counts.values()),
        "rolling_capital": capital,
        "capital_by_mode": capital_by_mode,
        "cargo_capacity": capacity,
        "profit_total": sum(profits) if profits else 0,
        "profit_by_mode": profit_by_mode,
        "profit_per_vehicle": (statistics.mean(profits) if profits else None),
    }


def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    ratings = station_ratings(chunks)
    vehs = vehicle_breakdown(chunks)
    veh_dec = decode_vehicles(chunks.get("VEHS"), target_owner=0)
    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "company_value": last.get("company_value", 0),
        "profit_year": year_profit(closed) or 0,
        "profit_quarter": quarter_profit(last) or 0,
        "performance_history": last.get("performance_history", 0),
        "delivered_cargo": last.get("delivered_cargo", 0),
        "money": player.get("money", 0),
        "current_loan": player.get("current_loan", 0),
        # H3 : n_vehicles est le nombre d'unites pilotables, pas le nombre brut d'entrees VEHS.
        # Fail-closed comme les harnais C66 actuels si le chunk physique est incoherent.
        "n_vehicles": veh_dec["primary_vehicles_count"] if veh_dec["chunk_valid"] else None,
        "vehs_chunk_valid": veh_dec["chunk_valid"],
        "vehs_chunk_error": veh_dec["chunk_error"],
        "vehicles_by_mode": vehs["by_mode"],
        "vehicles_capital": vehs["rolling_capital"],
        "n_stations": len(chunks.get("STNN") or {}),
        "median_station_rating": (statistics.median(ratings) if ratings else 0),
    },)


def extract_annual_snapshots(rows, starting_year=1970, total_years=3):
    by_run = defaultdict(list)
    for r in rows:
        key = (r["arm"], r["seed"])
        by_run[key].append(r)
    snapshots = {}
    for key, series in by_run.items():
        series.sort(key=lambda x: x["date"])
        year_records = {}
        for y in range(1, total_years + 1):
            target_year = starting_year + y - 1
            candidates = [r for r in series if r["date"].startswith(f"{target_year}-12") or r["date"].startswith(f"{target_year}-11")]
            if candidates:
                year_records[y] = candidates[-1]
            else:
                prior = [r for r in series if r["date"] <= f"{target_year}-12-31"]
                year_records[y] = (prior[-1] if prior else series[0]) if series else {}
        snapshots[key] = year_records
    return snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years",   type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds",   nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out",     type=Path, default=ROOT / "results" / "bench_1v1_3y_10seeds.json")
    args = parser.parse_args()

    enable_savegame_cleanup()

    arms = {
        "OpexAI":   local_folder(str(ROOT / "ai" / "OpexAI"),       "OpexAI",   ()),
        "AAAHogEx": local_folder(str(ROOT / "ai" / AAAHOGEX_DIR),   "AAAHogEx", ()),
    }

    experiments = []
    days = 365 * args.years
    cfg  = make_cfg(STARTING_YEAR)

    for arm_name, ai_spec in arms.items():
        for seed in args.seeds:
            experiments.append({
                "bench_arm":      arm_name,
                "seed":           seed,
                "days":           days,
                "openttd_config": cfg,
                "ais":            (ai_spec,),
            })

    print(f"=== Lancement Banc 1v1 OpexAI vs AAAHogEx : {len(arms)} IA x {len(args.seeds)} graines x {args.years} ans ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    snapshots = extract_annual_snapshots(rows, starting_year=STARTING_YEAR, total_years=args.years)
    S = args.seeds

    print("\n" + "=" * 115)
    print(f"BANC 1v1 OPEXAI vs AAAHOGEX — {args.years} ANS ({len(S)} GRAINES)")
    print("=" * 115)

    for y in range(1, args.years + 1):
        actual_year = STARTING_YEAR + y - 1
        print(f"\n--- ANNEE {y} ({actual_year}) ---")
        hdr = f"{'Graine':<7} | {'Valeur OpexAI vs AAAHogEx':<36} | {'Profit/an Opex vs AAA':<28} | {'Score O/A':<14} | {'Vehs O/A'}"
        print(hdr)
        print("-" * len(hdr))
        for s in S:
            op = snapshots.get(("OpexAI",   s), {}).get(y, {})
            aa = snapshots.get(("AAAHogEx", s), {}).get(y, {})
            op_v, aa_v = op.get("company_value", 0),       aa.get("company_value", 0)
            op_p, aa_p = op.get("profit_year", 0),          aa.get("profit_year", 0)
            op_s, aa_s = op.get("performance_history", 0),  aa.get("performance_history", 0)
            op_n, aa_n = op.get("n_vehicles", 0),           aa.get("n_vehicles", 0)
            ratio = (op_v / aa_v * 100) if aa_v > 0 else 0
            print(f"{s:<7} | {op_v:>10,.0f} vs {aa_v:>10,.0f} ({ratio:>5.1f}%) | {op_p:>9,.0f} vs {aa_p:>9,.0f} | {op_s:>4} vs {aa_s:>4} | {op_n:>3} vs {aa_n:>3}")
        print("-" * len(hdr))

        def _means(arm, key): return [snapshots.get((arm, s), {}).get(y, {}).get(key, 0) for s in S]
        for label, fn in [("MOYENNE", statistics.mean), ("MEDIANE", statistics.median)]:
            ov, av = fn(_means("OpexAI","company_value")),    fn(_means("AAAHogEx","company_value"))
            op2,ap2= fn(_means("OpexAI","profit_year")),      fn(_means("AAAHogEx","profit_year"))
            os2,as2= fn(_means("OpexAI","performance_history")),fn(_means("AAAHogEx","performance_history"))
            on2,an2= fn(_means("OpexAI","n_vehicles")),       fn(_means("AAAHogEx","n_vehicles"))
            print(f"{label} | {ov:>10,.0f} vs {av:>10,.0f} ({(ov/av*100 if av else 0):>5.1f}%) | {op2:>9,.0f} vs {ap2:>9,.0f} | {os2:>4.0f} vs {as2:>4.0f} | {on2:>3.0f} vs {an2:>3.0f}")

    # Trajectoire synthetique
    print("\n" + "=" * 115)
    print(f"TRAJECTOIRE (MOYENNES SUR {len(S)} GRAINES)")
    print("=" * 115)
    print(f"{'Annee':<10} | {'Val Opex':>14} | {'Val AAA':>14} | {'%V':>7} | {'Pft Opex':>13} | {'Pft AAA':>13} | {'%P':>7} | {'Veh O/A':>10} | {'Score O/A':>10}")
    print("-" * 115)
    for y in range(1, args.years + 1):
        actual_year = STARTING_YEAR + y - 1
        def m(arm, key): return statistics.mean([snapshots.get((arm, s), {}).get(y, {}).get(key, 0) for s in S])
        ov, av = m("OpexAI","company_value"), m("AAAHogEx","company_value")
        op, ap = m("OpexAI","profit_year"),   m("AAAHogEx","profit_year")
        on, an = m("OpexAI","n_vehicles"),    m("AAAHogEx","n_vehicles")
        os_, as_ = m("OpexAI","performance_history"), m("AAAHogEx","performance_history")
        print(f"An {y} ({actual_year}) | {ov:>13,.0f}£ | {av:>13,.0f}£ | {(ov/av*100 if av else 0):>6.1f}% | {op:>12,.0f}£ | {ap:>12,.0f}£ | {(op/ap*100 if ap else 0):>6.1f}% | {on:>4.0f} / {an:<4.0f} | {os_:>4.0f} / {as_:<4.0f}")
    print("-" * 115)

    # Mix modal annee finale
    print(f"\nMIX MODAL ANNEE {args.years}")
    print(f"{'Mode':<12} | {'OpexAI':>10} | {'AAAHogEx':>10} | {'%Opex':>8} | {'%AAA':>8}")
    print("-" * 60)
    for mode in VEHICLE_MODES:
        op_m  = statistics.mean([snapshots.get(("OpexAI",   s), {}).get(args.years, {}).get("vehicles_by_mode", {}).get(mode, 0) for s in S])
        aa_m  = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(args.years, {}).get("vehicles_by_mode", {}).get(mode, 0) for s in S])
        tot_op= statistics.mean([snapshots.get(("OpexAI",   s), {}).get(args.years, {}).get("n_vehicles", 0) for s in S])
        tot_aa= statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(args.years, {}).get("n_vehicles", 0) for s in S])
        print(f"{mode:<12} | {op_m:>10.1f} | {aa_m:>10.1f} | {(op_m/tot_op*100 if tot_op else 0):>7.1f}% | {(aa_m/tot_aa*100 if tot_aa else 0):>7.1f}%")
    print("-" * 60)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({
            "seeds":   args.seeds,
            "years":   args.years,
            "starting_year": STARTING_YEAR,
            "summary_snapshots": {
                f"{k[0]}_{k[1]}": {str(yr): rec for yr, rec in v.items()}
                for k, v in snapshots.items()
            },
        }, f, indent=2)
    print(f"\nResultats => {args.out}")


if __name__ == "__main__":
    main()
