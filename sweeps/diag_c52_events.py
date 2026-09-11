"""Diagnostic C52 : validation des evenements manquants (ET_VEHICLE_UNPROFITABLE et ET_VEHICLE_CRASHED).

Compare OpexAI baseline avec :
- OpexAI[event_vehicle_unprofitable=1] : mise au rebut des vehicules chroniquement deficitaires
- OpexAI[event_vehicle_crashed=1] : nettoyage d'inventaire et reconstitution sur tout crash
- OpexAI[event_vehicle_unprofitable=1,event_vehicle_crashed=1] : les deux combines

Respecte strictement le canevas AGENTS.md :
- keep(row) retourne un tuple (dict,)
- _check_output_with_script_debug injecte -d script=4
- metrics economiques PLYR[0]["old_economy"]
- comptage des decisions OPEX (UNPROFITABLE_RETIRE, UNPROFITABLE_SCRAP, VEHICLE_CRASHED, etc.)
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, make_cfg, quarter_profit, saved_year, script_failure_reason,
    year_profit, write_json_atomically,
)

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
    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if m:
            counts[m.group(4)] += 1
    return counts

def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    dec = parse_decisions(row.get("output", ""))
    py = year_profit(closed)

    stnn = chunks.get("STNN", {})
    stations_list = stnn.values() if isinstance(stnn, dict) else stnn
    ratings = [g["rating"] for s in stations_list for g in s.get("goods", []) if g.get("rating", 0) > 0]
    med_rating = statistics.median(ratings) if ratings else 0

    bench_run = row["experiment"].get("bench_run", [
        row["experiment"].get("bench_arm", "unknown"),
        row["experiment"].get("seed", 0),
        0
    ])
    arm, seed, repeat = bench_run[0], bench_run[1], bench_run[2]
    failure_reason = script_failure_reason(row.get("output", ""))

    return ({
        "arm": arm,
        "seed": seed,
        "repeat": repeat,
        "date": str(row.get("date", "")),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "median_station_rating": med_rating,
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "error": bool(row.get("error")) or bool(failure_reason),
        "failure_reason": failure_reason,
        "decisions": dict(dec),
    },)

def select_final_rows(rows, expected_last_year):
    by_run = {}
    for r in rows:
        key = (r["arm"], r["seed"], r["repeat"])
        by_run.setdefault(key, []).append(r)
    final = []
    for key, series in sorted(by_run.items(), key=lambda x: str(x[0])):
        series.sort(key=lambda item: item["date"])
        last = series[-1]
        last_year = saved_year(last["date"])
        incomplete = last_year is None or last_year < expected_last_year
        last["last_year"] = last_year
        last["expected_last_year"] = expected_last_year
        last["incomplete"] = incomplete
        if incomplete:
            last["error"] = True
            incomplete_reason = (
                f"incomplete_run: last autosave year "
                f"{last_year if last_year is not None else 'unknown'} < expected {expected_last_year}"
            )
            if last.get("failure_reason"):
                last["failure_reason"] = f"{last['failure_reason']}; {incomplete_reason}"
            else:
                last["failure_reason"] = incomplete_reason
        else:
            # keep() a deja capture le marqueur fatal du dernier autosave : ne pas
            # l'ecraser lorsqu'il atteint par hasard l'annee attendue.
            last["failure_reason"] = last.get("failure_reason") or script_failure_reason(last.get("output", ""))
        final.append(last)
    return final

def print_comparison(results, arms, seeds):
    by_arm_seed = defaultdict(dict)
    for r in results:
        by_arm_seed[r["arm"]][r["seed"]] = r

    metrics = ["company_value", "profit_year", "n_vehicles", "n_stations", "median_station_rating"]
    decision_keys = ["UNPROFITABLE_RETIRE", "UNPROFITABLE_SCRAP", "VEHICLE_CRASHED", "VEHICLE_UNPROFITABLE", "SCRAP_LINE"]

    print("\n" + "=" * 97)
    print(f"{'Arm':<45} | {'Val. Cie':>10} | {'Profit/an':>10} | {'Veh':>5} | {'Stn':>5} | {'Note':>5} | {'Err':>3}")
    print("-" * 97)
    for arm in arms:
        cv_list = [by_arm_seed[arm][s]["company_value"] for s in seeds if s in by_arm_seed[arm]]
        py_list = [by_arm_seed[arm][s]["profit_year"] for s in seeds if s in by_arm_seed[arm]]
        veh_list = [by_arm_seed[arm][s]["n_vehicles"] for s in seeds if s in by_arm_seed[arm]]
        stn_list = [by_arm_seed[arm][s]["n_stations"] for s in seeds if s in by_arm_seed[arm]]
        rat_list = [by_arm_seed[arm][s]["median_station_rating"] for s in seeds if s in by_arm_seed[arm]]
        err_list = [1 if by_arm_seed[arm][s].get("error") else 0 for s in seeds if s in by_arm_seed[arm]]
        mean_cv = statistics.mean(cv_list) if cv_list else 0
        mean_py = statistics.mean(py_list) if py_list else 0
        mean_veh = statistics.mean(veh_list) if veh_list else 0
        mean_stn = statistics.mean(stn_list) if stn_list else 0
        mean_rat = statistics.mean(rat_list) if rat_list else 0
        tot_err = sum(err_list)
        print(f"{arm:<45} | {mean_cv:>10.0f} | {mean_py:>10.0f} | {mean_veh:>5.1f} | {mean_stn:>5.1f} | {mean_rat:>5.1f} | {tot_err:>3}")
    print("=" * 97)

    # Paired comparison vs first arm (baseline)
    base_arm = arms[0]
    if len(arms) > 1:
        print("\nComparaisons appairees vs " + base_arm + ":")
        for arm in arms[1:]:
            print(f"\n--- {arm} vs {base_arm} ---")
            for m in ["company_value", "profit_year", "n_vehicles", "n_stations"]:
                diffs = []
                for s in seeds:
                    if s in by_arm_seed[arm] and s in by_arm_seed[base_arm]:
                        diffs.append(by_arm_seed[arm][s][m] - by_arm_seed[base_arm][s][m])
                if diffs:
                    mean_diff = statistics.mean(diffs)
                    wins = sum(1 for d in diffs if d > 0)
                    print(f"  {m:<25}: delta moyen = {mean_diff:>+10.1f} (gains: {wins}/{len(diffs)})")

    # Decisions comparison
    print("\nDecisions OPEX observees (totaux par arm sur les graines) :")
    print(f"{'Decision':<25} | " + " | ".join(f"{arm[:18]:>18}" for arm in arms))
    print("-" * (28 + 21 * len(arms)))
    for dk in decision_keys:
        vals = []
        for arm in arms:
            tot = sum(by_arm_seed[arm][s].get("decisions", {}).get(dk, 0) for s in seeds if s in by_arm_seed[arm])
            vals.append(tot)
        if any(v > 0 for v in vals):
            print(f"{dk:<25} | " + " | ".join(f"{v:>18}" for v in vals))
    print("-" * (28 + 21 * len(arms)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 2026])
    parser.add_argument("--arms", nargs="+", default=[
        "OpexAI",
        "OpexAI[event_vehicle_unprofitable=1,c52_unprofitable_log=1]",
        "OpexAI[event_vehicle_crashed=1,c52_crash_log=1]",
        "OpexAI[event_vehicle_unprofitable=1,event_vehicle_crashed=1,c52_unprofitable_log=1,c52_crash_log=1]",
    ])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=Path("results/diag_c52_events_6y_5seeds.json"))
    args = parser.parse_args()

    enable_savegame_cleanup()
    built = build_arms(args.arms)
    print(f"Lancement diagnostic C52 : {len(args.arms)} bras, {len(args.seeds)} graines, {args.years} ans...")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built, args.seeds, args.years, 1, args.starting_year),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    expected_last_year = args.starting_year + args.years - 1
    rows = select_final_rows(rows, expected_last_year)

    print_comparison(rows, args.arms, args.seeds)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "years": args.years,
            "seeds": args.seeds,
            "arms": args.arms,
            "starting_year": args.starting_year,
            "expected_last_year": expected_last_year,
            "results": rows,
        }
        write_json_atomically(args.out, payload)
        print(f"\nResultats ecrits dans {args.out}")

if __name__ == "__main__":
    main()
