"""Diagnostic C42 : validation de l'invalidation réactive et des gardes de subventions.

Compare baseline OpexAI vs OpexAI[c42_subsidies=1,c42_subsidy_log=1] sur 5 graines x 6 ans.
Mesure :
- Company value et profit annuel
- Nombre de gares et véhicules
- Événements de subventions (offres, expirations, builds, gains, discards)
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
from bench_v2 import (
    build_arms,
    enable_savegame_cleanup,
    experiments,
    make_cfg,
    quarter_profit,
    write_json_atomically,
    year_profit,
)

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
STARTING_YEAR = 1970
DEFAULT_SEEDS = [42, 100, 12345, 7, 999]

_real_check_output = openttdlab.subprocess.check_output
def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)
openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")

def parse_decisions(output):
    counts = Counter()
    subsidy_details = Counter()
    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if m:
            event_name = m.group(4)
            detail = m.group(5)
            counts[event_name] += 1
            if "SUBSIDY" in event_name or "subsidy" in detail:
                if "reason=" in detail:
                    reason = detail.split("reason=")[1].split()[0]
                    subsidy_details[f"{event_name}:{reason}"] += 1
                else:
                    subsidy_details[event_name] += 1
    return counts, subsidy_details

def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    dec, sub_dec = parse_decisions(row.get("output", ""))
    py = year_profit(closed)

    stnn = chunks.get("STNN", {})
    stations_list = stnn.values() if isinstance(stnn, dict) else stnn
    ratings = [g["rating"] for s in stations_list for g in s.get("goods", []) if g.get("rating", 0) > 0]
    med_rating = statistics.median(ratings) if ratings else 0

    exp = row.get("experiment", {})
    if "bench_run" in exp:
        arm = exp["bench_run"][0]
        seed = exp["bench_run"][1]
    else:
        arm = exp.get("bench_arm", "unknown")
        seed = exp.get("seed", 0)

    return ({
        "arm": arm,
        "seed": seed,
        "date": str(row.get("date", "")),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "median_station_rating": med_rating,
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "decisions": dict(dec),
        "subsidy_details": dict(sub_dec),
    },)  # ⚠️ VIRGULE OBLIGATOIRE : tuple à 1 élément

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=Path("results/diag_c42_subsidies_6y_5seeds.json"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    enable_savegame_cleanup()

    arms = [
        "OpexAI",
        "OpexAI[c42_subsidies=1,c42_subsidy_log=1]",
    ]
    built_arms = build_arms(arms)
    cfg = make_cfg(STARTING_YEAR)

    print(f"=== Diagnostic C42 : {len(arms)} bras x {len(args.seeds)} graines x {args.years} ans ===")
    exps = experiments(built_arms, args.seeds, args.years, repeats=1, starting_year=STARTING_YEAR)

    raw_results = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=exps,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    # Regrouper par run et ne garder que le dernier état
    by_run = defaultdict(list)
    for r in raw_results:
        key = (r["arm"], r["seed"])
        by_run[key].append(r)

    final_results = []
    for key, series in sorted(by_run.items()):
        series.sort(key=lambda x: x["date"])
        final_results.append(series[-1])

    # Regrouper les résultats par graine et par bras
    by_arm = defaultdict(list)
    by_seed = defaultdict(dict)
    for r in final_results:
        arm = r["arm"]
        seed = r["seed"]
        by_arm[arm].append(r)
        by_seed[seed][arm] = r

    print("\n=== Comparaison appariée par graine ===")
    header = f"{'Graine':<8} | {'CV Base (£)':<14} | {'CV Sub (£)':<14} | {'Delta (£)':<12} | {'Gares B/S':<10} | {'Vehs B/S':<10} | {'Sub Builds':<10} | {'Sub Won':<8}"
    print(header)
    print("-" * len(header))

    deltas = []
    for seed in args.seeds:
        base = by_seed[seed].get("OpexAI", {})
        sub = by_seed[seed].get("OpexAI[c42_subsidies=1,c42_subsidy_log=1]", {})
        cv_base = base.get("company_value", 0)
        cv_sub = sub.get("company_value", 0)
        delta = cv_sub - cv_base
        deltas.append(delta)
        st_b = base.get("n_stations", 0)
        st_s = sub.get("n_stations", 0)
        veh_b = base.get("n_vehicles", 0)
        veh_s = sub.get("n_vehicles", 0)
        sub_builds = sub.get("decisions", {}).get("C42_SUBSIDY_BUILD", 0)
        sub_won = sub.get("decisions", {}).get("C42_SUBSIDY_WON", 0)
        print(f"{seed:<8} | {cv_base:>14,} | {cv_sub:>14,} | {delta:>+12,} | {st_b:>4}/{st_s:<4} | {veh_b:>4}/{veh_s:<4} | {sub_builds:>10} | {sub_won:>8}")

    print("-" * len(header))
    mean_base = statistics.mean([r["company_value"] for r in by_arm["OpexAI"]]) if by_arm["OpexAI"] else 0
    mean_sub = statistics.mean([r["company_value"] for r in by_arm["OpexAI[c42_subsidies=1,c42_subsidy_log=1]"]]) if by_arm["OpexAI[c42_subsidies=1,c42_subsidy_log=1]"] else 0
    mean_delta = statistics.mean(deltas) if deltas else 0
    print(f"{'Moyenne':<8} | {int(mean_base):>14,} | {int(mean_sub):>14,} | {int(mean_delta):>+12,} |")

    # Détails des événements subventions
    print("\n=== Événements de subventions cumulés (Candidate) ===")
    total_events = Counter()
    for r in by_arm["OpexAI[c42_subsidies=1,c42_subsidy_log=1]"]:
        for k, v in r.get("subsidy_details", {}).items():
            total_events[k] += v
        for k, v in r.get("decisions", {}).items():
            if "SUBSIDY" in k:
                total_events[k] += v
    for k, v in sorted(total_events.items()):
        print(f"  {k:<45}: {v}")

    write_json_atomically(args.out, {
        "seeds": args.seeds,
        "years": args.years,
        "results": final_results,
    })
    print(f"\nRapport écrit dans {args.out}")

if __name__ == "__main__":
    main()
