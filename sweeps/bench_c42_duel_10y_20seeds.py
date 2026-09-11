"""Banc apparié C42 à 3 configurations d'expériences sur 20 graines x 10 ans :

1. OpexAI (solo, c42_subsidies=0, baseline)
2. OpexAI[c42_subsidies=1] (solo, avec subventions C42)
3. Duel OpexAI[c42_subsidies=1] vs AAAHogEx (carte partagée)

Enregistre les métriques pour les 4 bras résultants :
- OpexAI (solo baseline)
- OpexAI[c42_subsidies=1] (solo)
- OpexAI[c42]_duel (en duel partagé)
- AAAHogEx_duel (dans le duel partagé)

Sortie : results/bench_c42_duel_10y_20seeds.json
"""
import argparse
import inspect
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    SEEDS,
    SUCCESS_METRICS,
    arm_statistics,
    enable_savegame_cleanup,
    make_cfg,
    paired_comparisons,
    quarter_profit,
    script_failure_reason,
    station_ratings,
    summarise,
    write_json_atomically,
    year_profit,
)
import bench_v2

STARTING_YEAR = 1970
AAAHOGEX_DIR = "AAAHogEx-115"
CHECKPOINT_PATH = None

ARMS = (
    "OpexAI",
    "OpexAI[c42_subsidies=1]",
    "OpexAI[c42]_duel",
    "AAAHogEx_duel",
)


def append_checkpoint(record):
    global CHECKPOINT_PATH
    if CHECKPOINT_PATH is None:
        return
    encoded = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(CHECKPOINT_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, encoded)
    finally:
        os.close(fd)


def _first(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        if "owner" in value or "common" in value or "base" in value or "goods" in value or "xy" in value:
            return value
        return next(iter(value.values()), None)
    return value


def vehicle_owner(vehicle):
    if not isinstance(vehicle, dict):
        return None
    for kind in ("train", "roadveh", "ship", "aircraft"):
        body = _first(vehicle.get(kind))
        if not isinstance(body, dict):
            continue
        common = _first(body.get("common"))
        if isinstance(common, dict):
            return common.get("owner")
    return None


def station_owner(station):
    if not isinstance(station, dict):
        return None
    body = _first(station.get("normal"))
    if body is None:
        body = station
    if not isinstance(body, dict):
        return None
    base = _first(body.get("base"))
    return base.get("owner") if isinstance(base, dict) else None


def extract_company_record(chunks, owner, run_key, date, output=None):
    players = chunks.get("PLYR") or {}
    player = players.get(owner) or players.get(str(owner)) or {}
    closed = player.get("old_economy") or []
    last_closed = closed[0] if closed else {}
    ratings = station_ratings(chunks, owner=owner)
    vehs = chunks.get("VEHS") or {}
    stnn = chunks.get("STNN") or {}

    is_solo = (len(players) <= 1)
    if is_solo and owner == 0:
        n_vehs = len(vehs)
        n_stns = len(stnn)
    else:
        n_vehs = sum(1 for v in vehs.values() if vehicle_owner(v) == owner)
        n_stns = sum(1 for s in stnn.values() if station_owner(s) == owner)

    return {
        "run": run_key,
        "date": str(date),
        "company_value": last_closed.get("company_value", 0),
        "performance_history": last_closed.get("performance_history", 0),
        "income_last_year": last_closed.get("income", 0),
        "expenses_last_year": last_closed.get("expenses", 0),
        "profit": quarter_profit(last_closed),
        "profit_year": year_profit(closed),
        "median_station_rating": (statistics.median(ratings) if ratings else None),
        "n_station_ratings": len(ratings),
        "money": player.get("money", 0),
        "current_loan": player.get("current_loan", 0),
        "months_of_bankruptcy": player.get("months_of_bankruptcy", 0),
        "n_vehicles": n_vehs,
        "n_stations": n_stns,
        "openttd_output": output,
    }


def keep(row):
    chunks = row.get("chunks", {})
    date = row.get("date", "")
    output = row.get("output", "")
    is_duel = row["experiment"].get("is_duel", False)
    seed = row["experiment"]["seed"]
    repeat = row["experiment"].get("repeat", 0)

    if is_duel:
        rec0 = extract_company_record(chunks, 0, ["OpexAI[c42]_duel", seed, repeat], date, output)
        rec1 = extract_company_record(chunks, 1, ["AAAHogEx_duel", seed, repeat], date, "")
        append_checkpoint(rec0)
        append_checkpoint(rec1)
        return (rec0, rec1)
    else:
        arm_name = row["experiment"]["bench_arm"]
        rec = extract_company_record(chunks, 0, [arm_name, seed, repeat], date, output)
        append_checkpoint(rec)
        return (rec,)


def make_experiments_plan(seeds, years):
    cfg = make_cfg(STARTING_YEAR)
    days = 365 * years
    opex_baseline = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ())
    opex_c42 = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("c42_subsidies", 1),))
    aaahogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())

    exps = []
    # 1. Solo baseline
    for s in seeds:
        exps.append({
            "seed": s,
            "days": days,
            "openttd_config": cfg,
            "ais": (opex_baseline,),
            "bench_arm": "OpexAI",
            "is_duel": False,
            "repeat": 0,
        })
    # 2. Solo C42
    for s in seeds:
        exps.append({
            "seed": s,
            "days": days,
            "openttd_config": cfg,
            "ais": (opex_c42,),
            "bench_arm": "OpexAI[c42_subsidies=1]",
            "is_duel": False,
            "repeat": 0,
        })
    # 3. Duel partagé C42 vs AAAHogEx
    for s in seeds:
        exps.append({
            "seed": s,
            "days": days,
            "openttd_config": cfg,
            "ais": (opex_c42, aaahogex),
            "bench_arm": "duel",
            "is_duel": True,
            "repeat": 0,
        })
    return exps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "bench_c42_duel_10y_20seeds.json")
    args = parser.parse_args()

    global CHECKPOINT_PATH
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    bench_v2.CHECKPOINT_PATH = CHECKPOINT_PATH
    enable_savegame_cleanup()

    exps = make_experiments_plan(args.seeds, args.years)
    print(f"=== Lancement Banc C42 + Duel AAAHogEx : {len(exps)} parties ({len(args.seeds)} graines x {args.years} ans, 3 configurations) ===")
    print(f"Workers: {args.max_workers} | Sortie: {out}")

    rows = list(run_experiments(
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

    summary = summarise(rows)
    for record in summary:
        record.pop("openttd_output", "")
    failed = [record for record in summary if not record["run_ok"]]

    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "arms": list(ARMS),
        "design": "3 configurations: OpexAI solo, OpexAI[c42_subsidies=1] solo, duel partagé OpexAI[c42_subsidies=1] vs AAAHogEx",
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": [
            {"arm": record["arm"], "seed": record["seed"], "failure_reason": record["failure_reason"]}
            for record in failed
        ],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(out, payload)

    print(f"\n=== Resultats ({len(failed)} echecs) ===")
    stats = payload["statistics"]
    for arm in ARMS:
        s = stats.get(arm, {})
        cv = s.get("company_value", {}).get("mean")
        py = s.get("profit_year", {}).get("mean")
        sc = s.get("performance_history", {}).get("mean")
        print(f"[{arm}] CV: {cv:,.0f} £ | Profit/an: {py:,.0f} £ | Score: {sc:.1f}" if cv is not None and py is not None and sc is not None else f"[{arm}] data incomplete")

    print("\n=== Comparaisons appariées clés ===")
    for comp in payload["paired_comparisons"]:
        a, b = comp["arm_a"], comp["arm_b"]
        # Afficher en priorité les paires pertinentes
        if (a == "OpexAI" and b == "OpexAI[c42_subsidies=1]") or \
           (a == "OpexAI[c42]_duel" and b == "AAAHogEx_duel") or \
           (a == "OpexAI[c42_subsidies=1]" and b == "OpexAI[c42]_duel"):
            print(f"\n--- {a} vs {b} ---")
            for metric in ("company_value", "profit_year", "performance_history", "median_station_rating"):
                m = comp["metrics"].get(metric, {})
                diff = m.get("mean_difference_percent")
                wins = m.get("arm_a_beats_arm_b")
                n = m.get("n")
                print(f"  {metric:<24} : d% = {diff:+.2f}% | victoires {a} = {wins}/{n}")

    if failed:
        raise SystemExit(f"Banc invalide : {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
