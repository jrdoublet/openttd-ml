"""Banc comparatif 1v1 OpexAI vs AAAHogEx : 5 graines x 5 ans.

Compare les chiffres principaux annee par annee (Annees 1 a 5, 1970 a 1974) :
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
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit, station_ratings

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
DEFAULT_YEARS = 5
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
            # Sous-compartiment (soute d'avion, wagon de train)
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

    record = {
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
        "n_vehicles": vehs["n_units"],
        "vehicles_by_mode": vehs["by_mode"],
        "vehicles_capital": vehs["rolling_capital"],
        "n_stations": len(chunks.get("STNN") or {}),
        "median_station_rating": (statistics.median(ratings) if ratings else 0),
    }
    return (record,)


def extract_annual_snapshots(rows, starting_year=1970, total_years=5):
    """Extrait l'enregistrement de fin d'annee (vers decembre) pour chaque annee 1..total_years."""
    by_run = defaultdict(list)
    for r in rows:
        key = (r["arm"], r["seed"])
        by_run[key].append(r)

    snapshots = {}  # (arm, seed) -> {year: record}
    for key, series in by_run.items():
        series.sort(key=lambda x: x["date"])
        year_records = {}
        for y in range(1, total_years + 1):
            target_year = starting_year + y - 1
            # Chercher dans la plage de novembre a decembre de l'annee cible
            candidates = [r for r in series if r["date"].startswith(f"{target_year}-12") or r["date"].startswith(f"{target_year}-11")]
            if candidates:
                year_records[y] = candidates[-1]
            else:
                # Repli sur le dernier enregistrement <= 31 decembre de l'annee
                prior = [r for r in series if r["date"] <= f"{target_year}-12-31"]
                if prior:
                    year_records[y] = prior[-1]
                elif series:
                    year_records[y] = series[0]
        snapshots[key] = year_records
    return snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "bench_1v1_5y_5seeds.json")
    args = parser.parse_args()

    enable_savegame_cleanup()

    arms = {
        "OpexAI": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ()),
        "AAAHogEx": local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ()),
    }

    experiments = []
    days = 365 * args.years
    cfg = make_cfg(STARTING_YEAR)

    for arm_name, ai_spec in arms.items():
        for seed in args.seeds:
            experiments.append({
                "bench_arm": arm_name,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (ai_spec,),
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

    print("\n" + "=" * 115)
    print(f"BANC 1v1 OPEXAI vs AAAHOGEX — COMPARAISON ANNUELLE SUR {args.years} ANS ({len(args.seeds)} GRAINES)")
    print("=" * 115)

    for y in range(1, args.years + 1):
        actual_year = STARTING_YEAR + y - 1
        print(f"\n--- ANNEE {y} ({actual_year}) ---")
        header = f"{'Graine':<7} | {'Valeur OpexAI vs AAAHogEx':<32} | {'Profit An OpexAI vs AAA':<30} | {'Score Opex vs AAA':<20} | {'Vehicules Opex vs AAA':<22}"
        print(header)
        print("-" * len(header))

        for s in args.seeds:
            op = snapshots.get(("OpexAI", s), {}).get(y, {})
            aa = snapshots.get(("AAAHogEx", s), {}).get(y, {})

            op_v, aa_v = op.get("company_value", 0), aa.get("company_value", 0)
            op_p, aa_p = op.get("profit_year", 0), aa.get("profit_year", 0)
            op_s, aa_s = op.get("performance_history", 0), aa.get("performance_history", 0)
            op_veh, aa_veh = op.get("n_vehicles", 0), aa.get("n_vehicles", 0)

            ratio_v = (op_v / aa_v * 100) if aa_v > 0 else 0
            v_str = f"{op_v:>10,.0f} vs {aa_v:>10,.0f} ({ratio_v:>4.1f}%)"
            p_str = f"{op_p:>9,.0f} vs {aa_p:>9,.0f}"
            s_str = f"{op_s:>4} vs {aa_s:>4}"
            veh_str = f"{op_veh:>3} vs {aa_veh:>3}"

            print(f"{s:<7} | {v_str:<32} | {p_str:<30} | {s_str:<20} | {veh_str:<22}")

        print("-" * len(header))

        # Moyennes et medianes pour l'annee y
        op_vals = [snapshots.get(("OpexAI", s), {}).get(y, {}).get("company_value", 0) for s in args.seeds]
        aa_vals = [snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("company_value", 0) for s in args.seeds]
        op_profs = [snapshots.get(("OpexAI", s), {}).get(y, {}).get("profit_year", 0) for s in args.seeds]
        aa_profs = [snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("profit_year", 0) for s in args.seeds]
        op_scores = [snapshots.get(("OpexAI", s), {}).get(y, {}).get("performance_history", 0) for s in args.seeds]
        aa_scores = [snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("performance_history", 0) for s in args.seeds]
        op_vehs = [snapshots.get(("OpexAI", s), {}).get(y, {}).get("n_vehicles", 0) for s in args.seeds]
        aa_vehs = [snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("n_vehicles", 0) for s in args.seeds]

        print(f"MOYENNE | {statistics.mean(op_vals):>10,.0f} vs {statistics.mean(aa_vals):>10,.0f} ({(statistics.mean(op_vals)/statistics.mean(aa_vals)*100 if statistics.mean(aa_vals) else 0):>4.1f}%) | {statistics.mean(op_profs):>9,.0f} vs {statistics.mean(aa_profs):>9,.0f}           | {statistics.mean(op_scores):>4.0f} vs {statistics.mean(aa_scores):>4.0f}         | {statistics.mean(op_vehs):>3.0f} vs {statistics.mean(aa_vehs):>3.0f}")
        print(f"MEDIANE | {statistics.median(op_vals):>10,.0f} vs {statistics.median(aa_vals):>10,.0f} ({(statistics.median(op_vals)/statistics.median(aa_vals)*100 if statistics.median(aa_vals) else 0):>4.1f}%) | {statistics.median(op_profs):>9,.0f} vs {statistics.median(aa_profs):>9,.0f}           | {statistics.median(op_scores):>4.0f} vs {statistics.median(aa_scores):>4.0f}         | {statistics.median(op_vehs):>3.0f} vs {statistics.median(aa_vehs):>3.0f}")

    # Tableau recapitulatif de la trajectoire sur les 5 ans
    print("\n" + "=" * 115)
    print("TRAJECTOIRE SYNTHETIQUE ANNEE PAR ANNEE (MOYENNES SUR LES 5 GRAINES)")
    print("=" * 115)
    print(f"{'Annee':<8} | {'Valeur OpexAI':>14} | {'Valeur AAA':>14} | {'Ratio V':>8} | {'Profit OpexAI':>14} | {'Profit AAA':>14} | {'Ratio P':>8} | {'Veh Opex/AAA':>14} | {'Score O/A':>10}")
    print("-" * 115)
    for y in range(1, args.years + 1):
        actual_year = STARTING_YEAR + y - 1
        op_v = statistics.mean([snapshots.get(("OpexAI", s), {}).get(y, {}).get("company_value", 0) for s in args.seeds])
        aa_v = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("company_value", 0) for s in args.seeds])
        op_p = statistics.mean([snapshots.get(("OpexAI", s), {}).get(y, {}).get("profit_year", 0) for s in args.seeds])
        aa_p = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("profit_year", 0) for s in args.seeds])
        op_veh = statistics.mean([snapshots.get(("OpexAI", s), {}).get(y, {}).get("n_vehicles", 0) for s in args.seeds])
        aa_veh = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("n_vehicles", 0) for s in args.seeds])
        op_sc = statistics.mean([snapshots.get(("OpexAI", s), {}).get(y, {}).get("performance_history", 0) for s in args.seeds])
        aa_sc = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(y, {}).get("performance_history", 0) for s in args.seeds])

        rv = (op_v / aa_v * 100) if aa_v > 0 else 0
        rp = (op_p / aa_p * 100) if aa_p > 0 else 0
        veh_str = f"{op_veh:.0f} / {aa_veh:.0f}"
        sc_str = f"{op_sc:.0f} / {aa_sc:.0f}"

        print(f"An {y} ({actual_year}) | {op_v:>13,.0f}£ | {aa_v:>13,.0f}£ | {rv:>7.1f}% | {op_p:>13,.0f}£ | {aa_p:>13,.0f}£ | {rp:>7.1f}% | {veh_str:>14} | {sc_str:>10}")

    print("-" * 115)

    # Mix modal compare An 5
    print("\n" + "=" * 115)
    print(f"MIX MODAL EN ANNEE {args.years} (MOYENNE DU NOMBRE DE VEHICULES PAR MODE)")
    print("=" * 115)
    print(f"{'Mode':<12} | {'OpexAI (An 5)':<18} | {'AAAHogEx (An 5)':<18} | {'Part OpexAI':<14} | {'Part AAAHogEx':<14}")
    print("-" * 85)
    for mode in VEHICLE_MODES:
        op_m = statistics.mean([snapshots.get(("OpexAI", s), {}).get(args.years, {}).get("vehicles_by_mode", {}).get(mode, 0) for s in args.seeds])
        aa_m = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(args.years, {}).get("vehicles_by_mode", {}).get(mode, 0) for s in args.seeds])
        tot_op = statistics.mean([snapshots.get(("OpexAI", s), {}).get(args.years, {}).get("n_vehicles", 0) for s in args.seeds])
        tot_aa = statistics.mean([snapshots.get(("AAAHogEx", s), {}).get(args.years, {}).get("n_vehicles", 0) for s in args.seeds])
        pct_op = (op_m / tot_op * 100) if tot_op > 0 else 0
        pct_aa = (aa_m / tot_aa * 100) if tot_aa > 0 else 0
        print(f"{mode:<12} | {op_m:>14.1f}   | {aa_m:>14.1f}   | {pct_op:>11.1f}% | {pct_aa:>11.1f}%")
    print("-" * 85)

    with open(args.out, "w") as f:
        json.dump({
            "seeds": args.seeds,
            "years": args.years,
            "starting_year": STARTING_YEAR,
            "summary_snapshots": {
                f"{k[0]}_{k[1]}": {str(yr): rec for yr, rec in v.items()}
                for k, v in snapshots.items()
            },
        }, f, indent=2)
    print(f"\nResultats detailles enregistres dans : {args.out}")


if __name__ == "__main__":
    main()
