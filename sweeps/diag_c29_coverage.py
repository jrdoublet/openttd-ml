"""Diagnostic et mesure de C29.4 (docs/taches.md C29.4).

Mesure la couverture multi-arrêts urbaine pour le rabattement :
Jusqu'à ceil(maisons / ROAD_STOP_CATCHMENT_HOUSES) gares distinctes par ville
sur le modèle AAAHogEx avec séparation spatiale >= 6 tuiles.

Compare deux bras :
1. control : feeder_town_coverage = 0 (arrêt unique par ville)
2. c29_4   : feeder_town_coverage = 1 (couverture multi-arrêts, nouveau défaut)

Mesure par bras et par graine :
- FEEDER_BUILD total
- FEEDER_BUILD par slot (slot 0 vs multi-stop slot >= 1)
- Villes avec multi-arrêts (>= 2 feeders)
- Liaisons aériennes neuves (air_builds)
- company_value, profit_year, performance_history, median_station_rating
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
DEFAULT_YEARS = 6
STARTING_YEAR = 1970

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_decisions(output):
    build_counts = Counter()
    feeder_by_mode = Counter()
    feeder_by_slot = Counter()
    feeders_by_town = Counter()
    refuse_counts = Counter()

    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if not m:
            continue
        kind = m.group(4)
        payload = m.group(5)
        kvs = {}
        for token in payload.split():
            if "=" in token:
                k, _, v = token.partition("=")
                kvs[k] = v

        if kind == "FEEDER_BUILD":
            build_counts["FEEDER"] += 1
            mode = kvs.get("hub_mode", "unknown")
            feeder_by_mode[mode] += 1
            slot = int(kvs.get("slot", 0))
            feeder_by_slot[slot] += 1
            src_tile = kvs.get("src", "")
            if src_tile:
                feeders_by_town[src_tile] += 1
        elif kind == "AIR_BUILD":
            build_counts["AIR"] += 1
        elif kind == "ROAD_BUILD":
            build_counts["ROAD"] += 1
        elif kind == "RAIL_BUILD":
            build_counts["RAIL"] += 1
        elif kind == "FEEDER_REFUSE":
            refuse_counts["FEEDER_REFUSE"] += 1
            reason = kvs.get("reason", "unknown")
            refuse_counts[f"refuse_{reason}"] += 1

    multi_towns = sum(1 for cnt in feeders_by_town.values() if cnt >= 2)

    return {
        "feeder_total": build_counts["FEEDER"],
        "feeder_air": feeder_by_mode["air"],
        "feeder_rail": feeder_by_mode["rail"],
        "feeder_slot0": feeder_by_slot[0],
        "feeder_multistop": sum(cnt for slot, cnt in feeder_by_slot.items() if slot >= 1),
        "towns_multistop": multi_towns,
        "air_builds": build_counts["AIR"],
        "road_builds": build_counts["ROAD"],
        "rail_builds": build_counts["RAIL"],
        "feeder_refuses": refuse_counts["FEEDER_REFUSE"],
    }


def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    dec = parse_decisions(row.get("output", ""))
    py = year_profit(closed)

    stnn = chunks.get("STNN", {})
    ratings = []
    for s in stnn.values() if isinstance(stnn, dict) else stnn:
        for g in s.get("goods", []):
            r = g.get("rating", 0)
            if r > 0:
                ratings.append(r)
    med_rating = statistics.median(ratings) if ratings else 0

    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "median_station_rating": med_rating,
        "money": (player or {}).get("money", 0),
        "current_loan": (player or {}).get("current_loan", 0),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "feeder_total": dec["feeder_total"],
        "feeder_air": dec["feeder_air"],
        "feeder_rail": dec["feeder_rail"],
        "feeder_slot0": dec["feeder_slot0"],
        "feeder_multistop": dec["feeder_multistop"],
        "towns_multistop": dec["towns_multistop"],
        "air_builds": dec["air_builds"],
        "road_builds": dec["road_builds"],
        "rail_builds": dec["rail_builds"],
        "feeder_refuses": dec["feeder_refuses"],
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_c29_coverage.json")
    args = parser.parse_args()

    enable_savegame_cleanup()

    arms = [
        ("control", {"decision_log": 1, "feeder_town_coverage": 0}),
        ("c29_4",   {"decision_log": 1, "feeder_town_coverage": 1}),
    ]

    experiments = []
    days = 365 * args.years
    cfg = make_cfg(STARTING_YEAR)

    for arm_name, overrides in arms:
        ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", tuple(overrides.items()))
        for seed in args.seeds:
            experiments.append({
                "bench_arm": arm_name,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (ai,),
            })

    print(f"=== Lancement diagnostic C29.4 : {len(arms)} bras x {len(args.seeds)} graines x {args.years} ans ===")
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

    by_arm = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)

    print("\n" + "=" * 105)
    print(f"DIAGNOSTIC C29.4 : COUVERTURE MULTI-ARRETS URBAINE ({args.years} ans, {len(args.seeds)} graines)")
    print("=" * 105)

    ctrl = {s: max((r for r in by_arm["control"] if r["seed"] == s), key=lambda r: r["date"]) for s in args.seeds}
    c29_4 = {s: max((r for r in by_arm["c29_4"] if r["seed"] == s), key=lambda r: r["date"]) for s in args.seeds}

    header = f"{'Graine':<7} | {'Feeders (C->29.4)':<18} | {'Multi-stop Fdr':<14} | {'Villes Multi':<12} | {'Valeur C -> 29.4':<26} | {'Profit An C -> 29.4':<24}"
    print(header)
    print("-" * len(header))

    for s in args.seeds:
        c, t = ctrl[s], c29_4[s]
        f_tot = f"{c['feeder_total']} -> {t['feeder_total']}"
        f_ms = f"{c['feeder_multistop']} -> {t['feeder_multistop']}"
        v_ms = f"{c['towns_multistop']} -> {t['towns_multistop']}"
        cv_pct = ((t['company_value'] - c['company_value']) / c['company_value'] * 100) if c['company_value'] != 0 else 0
        py_pct = ((t['profit_year'] - c['profit_year']) / c['profit_year'] * 100) if c['profit_year'] != 0 else 0
        cv = f"{c['company_value']:>8} -> {t['company_value']:>8} ({cv_pct:>+5.1f}%)"
        py = f"{c['profit_year']:>8} -> {t['profit_year']:>8} ({py_pct:>+5.1f}%)"
        print(f"{s:<7} | {f_tot:<18} | {f_ms:<14} | {v_ms:<12} | {cv:<26} | {py:<24}")

    print("-" * len(header))

    metrics = [
        ("feeder_total", "Feeders construits (total)", False),
        ("feeder_multistop", "Feeders multi-arrêts (slot >= 1)", False),
        ("towns_multistop", "Villes à arrêts multiples (>=2)", False),
        ("air_builds", "Liaisons aériennes neuves", False),
        ("company_value", "Valeur d'entreprise (£)", True),
        ("profit_year", "Profit annuel (£)", True),
        ("performance_history", "Score officiel (points)", False),
        ("median_station_rating", "Note de gare médiane", False),
        ("n_vehicles", "Nombre de véhicules", False),
        ("n_stations", "Nombre de gares/stations", False),
    ]

    print("\nSynthèse agrégée sur les 5 graines :")
    print(f"{'Métrique':<32} | {'Contrôle (moy)':<16} | {'C29.4 (moy)':<16} | {'Delta':<16} | {'Médiane C -> 29.4':<22}")
    print("-" * 110)

    for key, label, is_currency in metrics:
        c_vals = [ctrl[s][key] for s in args.seeds]
        t_vals = [c29_4[s][key] for s in args.seeds]
        mean_c = statistics.mean(c_vals)
        mean_t = statistics.mean(t_vals)
        med_c = statistics.median(c_vals)
        med_t = statistics.median(t_vals)
        delta = mean_t - mean_c
        pct = (delta / mean_c * 100) if mean_c != 0 else 0

        fmt = "{:,.0f}" if is_currency else "{:.1f}"
        c_str = fmt.format(mean_c)
        t_str = fmt.format(mean_t)
        d_str = f"{delta:+,.0f} ({pct:+.1f}%)" if is_currency else f"{delta:+.1f} ({pct:+.1f}%)"
        med_str = f"{fmt.format(med_c)} -> {fmt.format(med_t)}"
        print(f"{label:<32} | {c_str:<16} | {t_str:<16} | {d_str:<16} | {med_str:<22}")

    with open(args.out, "w") as f:
        json.dump({"seeds": args.seeds, "years": args.years, "summary": rows}, f, indent=2)
    print(f"\nRapport enregistré dans : {args.out}")


if __name__ == "__main__":
    main()
