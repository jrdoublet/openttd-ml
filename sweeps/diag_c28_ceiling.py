"""Diagnostic et validation de C28 (docs/taches.md C28).

Objet : Evaluer le remplacement du cliquet infini sans decroissance par un maximum
glissant sur les N derniers cycles pour capitalCeiling.

Compare les bras :
1. control : capital_ceiling_cycles = 0 (cliquet infini historique, jamais decroissant)
2. c28_n12 : capital_ceiling_cycles = 12 (fenetre glissante de 12 cycles ~ 1 an)
3. c28_n24 : capital_ceiling_cycles = 24 (fenetre glissante de 24 cycles ~ 2 ans)

Mesure par bras et par graine :
- company_value, profit_year, n_stations, n_vehicles
- Rejets vivier infinancables (VIVIER_INFUNDABLE) et evolution du ceiling
- Chantiers batis par mode (AIR_BUILD, ROAD_BUILD, RAIL_BUILD, FEEDER_BUILD)
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
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
DEFAULT_YEARS = 10
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
    infundable_total = 0
    ceilings = []

    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if not m:
            continue
        kind, rest = m.group(4), m.group(5)
        if "BUILD" in kind:
            build_counts[kind] += 1
        elif kind == "VIVIER_INFUNDABLE":
            fields = dict(t.split("=", 1) for t in rest.split() if "=" in t)
            infundable_total += int(fields.get("total", 0))
            if "ceiling" in fields:
                try:
                    ceilings.append(int(fields["ceiling"]))
                except ValueError:
                    pass

    return {
        "build_counts": dict(build_counts),
        "infundable_total": infundable_total,
        "ceilings_min": min(ceilings) if ceilings else 0,
        "ceilings_max": max(ceilings) if ceilings else 0,
        "ceilings_last": ceilings[-1] if ceilings else 0,
    }


def result_extractor(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    dec = parse_decisions(row.get("output", ""))
    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": year_profit(closed),
        "profit": quarter_profit(last_closed),
        "money": (player or {}).get("money", 0),
        "current_loan": (player or {}).get("current_loan", 0),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "decisions": dec,
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c28_ceiling.json")
    args = parser.parse_args()

    enable_savegame_cleanup()

    arms = [
        ("control", {"decision_log": 1, "capital_ceiling_cycles": 0}),
        ("c28_n24", {"decision_log": 1, "capital_ceiling_cycles": 24}),
        ("c28_n36", {"decision_log": 1, "capital_ceiling_cycles": 36}),
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

    print(f"=== Lancement du diagnostic C28 : {len(arms)} bras x {len(args.seeds)} graines x {args.years} ans ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=result_extractor,
        experiments=experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        )
    ))

    final_rows = {}
    for r in rows:
        final_rows[(r["arm"], r["seed"])] = r
    results_by_arm = defaultdict(list)
    for r in final_rows.values():
        results_by_arm[r["arm"]].append(r)
    rows = list(final_rows.values())

    print("\n" + "=" * 95)
    print(f"{'Arm':8} {'Seed':6} {'Valeur':>11} {'Profit_an':>11} {'Air':>5} {'Feed':>5} {'Rail':>5} {'Road':>5} {'Infund':>7} {'Ceil_Max':>9} {'Ceil_End':>9}")
    print("=" * 95)

    summary = {}
    for arm_name, _ in arms:
        arm_rows = sorted(results_by_arm[arm_name], key=lambda x: x["seed"])
        val_list = [(r.get("company_value") or 0) for r in arm_rows]
        prof_list = [(r.get("profit_year") or 0) for r in arm_rows]
        air_list = [r["decisions"]["build_counts"].get("AIR_BUILD", 0) for r in arm_rows]
        feeder_tot = [r["decisions"]["build_counts"].get("FEEDER_BUILD", 0) for r in arm_rows]
        rail_list = [r["decisions"]["build_counts"].get("RAIL_BUILD", 0) for r in arm_rows]
        road_list = [r["decisions"]["build_counts"].get("ROAD_BUILD", 0) for r in arm_rows]
        infund_tot = [r["decisions"].get("infundable_total", 0) for r in arm_rows]

        for r in arm_rows:
            s = r["seed"]
            bc = r["decisions"]["build_counts"]
            dec = r["decisions"]
            cv = r.get("company_value") or 0
            py = r.get("profit_year") or 0
            print(f"{arm_name:8} {s:6d} {cv:>10d}£ {py:>10d}£ "
                  f"{bc.get('AIR_BUILD', 0):>5d} {bc.get('FEEDER_BUILD', 0):>5d} "
                  f"{bc.get('RAIL_BUILD', 0):>5d} {bc.get('ROAD_BUILD', 0):>5d} "
                  f"{dec.get('infundable_total', 0):>7d} "
                  f"{dec.get('ceilings_max', 0):>9d} {dec.get('ceilings_last', 0):>9d}")

        summary[arm_name] = {
            "valeur_med": statistics.median(val_list),
            "valeur_mean": statistics.mean(val_list),
            "profit_med": statistics.median(prof_list),
            "profit_mean": statistics.mean(prof_list),
            "air_total": sum(air_list),
            "feeder_total": sum(feeder_tot),
            "rail_total": sum(rail_list),
            "road_total": sum(road_list),
            "infundable_total": sum(infund_tot),
        }
        print("-" * 95)

    print("\n=== RÉSUMÉ COMPARATIF ===")
    ctrl = summary["control"]
    for arm_name in ("c28_n24", "c28_n36"):
        s = summary[arm_name]
        print(f"\n--- {arm_name} vs control ---")
        print(f"Valeur médiane     : {ctrl['valeur_med']:>10.0f}£ -> {s['valeur_med']:>10.0f}£ ({(s['valeur_med']/ctrl['valeur_med']-1)*100:+.1f}%)")
        print(f"Valeur moyenne     : {ctrl['valeur_mean']:>10.0f}£ -> {s['valeur_mean']:>10.0f}£ ({(s['valeur_mean']/ctrl['valeur_mean']-1)*100:+.1f}%)")
        print(f"Profit an médian   : {ctrl['profit_med']:>10.0f}£ -> {s['profit_med']:>10.0f}£ ({(s['profit_med']/ctrl['profit_med']-1)*100:+.1f}%)")
        print(f"Profit an moyen    : {ctrl['profit_mean']:>10.0f}£ -> {s['profit_mean']:>10.0f}£ ({(s['profit_mean']/ctrl['profit_mean']-1)*100:+.1f}%)")
        print(f"Lignes Air total   : {ctrl['air_total']:>10d}  -> {s['air_total']:>10d}  ({s['air_total']-ctrl['air_total']:+d})")
        print(f"Feeders TOTAL      : {ctrl['feeder_total']:>10d}  -> {s['feeder_total']:>10d}  ({s['feeder_total']-ctrl['feeder_total']:+d})")
        print(f"Lignes Rail total  : {ctrl['rail_total']:>10d}  -> {s['rail_total']:>10d}  ({s['rail_total']-ctrl['rail_total']:+d})")
        print(f"Lignes Road total  : {ctrl['road_total']:>10d}  -> {s['road_total']:>10d}  ({s['road_total']-ctrl['road_total']:+d})")
        print(f"Infundables rejetés: {ctrl['infundable_total']:>10d}  -> {s['infundable_total']:>10d}  ({s['infundable_total']-ctrl['infundable_total']:+d})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"\nRapport complet écrit dans {args.out}")


if __name__ == "__main__":
    main()
