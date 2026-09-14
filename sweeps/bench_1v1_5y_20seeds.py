"""Banc de référence 1v1 en carte partagée OpexAI vs AAAHogEx (20 graines x 5 ans).

Post-09/09 Reference Benchmark :
- OpexAI (Player 0) contre AAAHogEx (Player 1) sur la même carte.
- 20 graines x 5 ans (1970-1975).
- Mesure les métriques standard (company_value, profit_year, performance_history,
  n_vehicles, n_stations, median_station_rating) et produit la comparaison appariée.
- Sortie : results/bench_1v1_5y_20seeds_reference.json (+ checkpoint .jsonl)
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
from physical_counters import decode_vehicles, decode_stations
import bench_v2

STARTING_YEAR = 1970
DEFAULT_YEARS = 5
AAAHOGEX_DIR = "AAAHogEx-115"
CHECKPOINT_PATH = None

ARMS = ("OpexAI", "AAAHogEx")


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
    veh_dec = decode_vehicles(chunks.get("VEHS"), target_owner=owner)
    stn_dec = decode_stations(chunks.get("STNN"), target_owner=owner)

    vehs_valid = veh_dec["chunk_valid"]
    stnn_valid = stn_dec["chunk_valid"]

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
        "physical_counters_version": veh_dec["schema_version"],
        "qualified_modes": veh_dec["qualified_modes"],
        "vehs_chunk_valid": vehs_valid,
        "vehs_chunk_error": veh_dec["chunk_error"],
        "stnn_chunk_valid": stnn_valid,
        "stnn_chunk_error": stn_dec["chunk_error"],
        "n_vehicles": veh_dec["vehicle_pool_entries"] if vehs_valid else None,
        "vehicle_pool_entries": veh_dec["vehicle_pool_entries"] if vehs_valid else None,
        "primary_vehicles": veh_dec["primary_vehicles_count"] if vehs_valid else None,
        "primary_vehicles_by_mode": veh_dec["primary_vehicles_by_mode"] if vehs_valid else None,
        "capacities_by_cargo": veh_dec["capacities_by_cargo"] if vehs_valid else None,
        "fleet_status": veh_dec["fleet_status"] if vehs_valid else None,
        "unclassified_vehicles": len(veh_dec["unclassified_entries"]),
        "n_stations": stn_dec["total_stations"] if stnn_valid else None,
        "n_multimodal_stations": stn_dec["n_multimodal_stations"] if stnn_valid else None,
        "stations_by_facility": stn_dec["stations_by_facility"] if stnn_valid else None,
        "unresolved_stations": len(stn_dec["unresolved_stations"]),
        "openttd_output": output,
    }


def keep(row):
    chunks = row.get("chunks", {})
    date = row.get("date", "")
    output = row.get("output", "")
    seed = row["experiment"]["seed"]
    repeat = row["experiment"].get("repeat", 0)

    rec0 = extract_company_record(chunks, 0, ["OpexAI", seed, repeat], date, output)
    rec1 = extract_company_record(chunks, 1, ["AAAHogEx", seed, repeat], date, "")
    append_checkpoint(rec0)
    append_checkpoint(rec1)
    return (rec0, rec1)


def make_experiments_plan(seeds, years):
    cfg = make_cfg(STARTING_YEAR)
    days = 365 * years
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ())
    aaahogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())

    exps = []
    for s in seeds:
        exps.append({
            "seed": s,
            "days": days,
            "openttd_config": cfg,
            "ais": (opex, aaahogex),
            "bench_arm": "duel",
            "is_duel": True,
            "repeat": 0,
        })
    return exps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "bench_1v1_5y_20seeds_reference.json")
    parser.add_argument("--selftest", action="store_true", help="Vérifie le décodage et le fail-closed sans lancer OpenTTD")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    global CHECKPOINT_PATH
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    bench_v2.CHECKPOINT_PATH = CHECKPOINT_PATH
    enable_savegame_cleanup()

    exps = make_experiments_plan(args.seeds, args.years)
    print(f"=== Lancement Banc 1v1 Duel OpexAI vs AAAHogEx : {len(exps)} parties ({len(args.seeds)} graines x {args.years} ans) ===")
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
        "design": "Duel partagé OpexAI (joueur 0) vs AAAHogEx (joueur 1)",
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

    print("\n" + "=" * 115)
    print(f"BANC 1v1 OPEXAI vs AAAHOGEX (CARTE PARTAGÉE) — BILAN {args.years} ANS ({len(args.seeds)} GRAINES)")
    print("=" * 115)
    header = f"{'Graine':<8} | {'Valeur Opex vs AAAHogEx':<32} | {'Profit An Opex vs AAA':<28} | {'Score O/A':<14} | {'Véhicules O/A':<16} | {'Gares O/A':<12}"
    print(header)
    print("-" * len(header))

    # Tableau par graine
    runs_by_seed = {}
    for r in summary:
        runs_by_seed[(r["arm"], r["seed"])] = r

    for s in args.seeds:
        op = runs_by_seed.get(("OpexAI", s), {})
        aa = runs_by_seed.get(("AAAHogEx", s), {})

        op_v, aa_v = op.get("company_value"), aa.get("company_value")
        op_p, aa_p = op.get("profit_year"), aa.get("profit_year")
        op_s, aa_s = op.get("performance_history"), aa.get("performance_history")
        op_veh, aa_veh = op.get("n_vehicles"), aa.get("n_vehicles")
        op_stn, aa_stn = op.get("n_stations"), aa.get("n_stations")

        v_str = (
            f"{op_v:>10,.0f} vs {aa_v:>10,.0f} ({(op_v / aa_v * 100) if aa_v else 0:>4.1f}%)"
            if (op_v is not None and aa_v is not None) else "FAIL"
        )
        p_str = f"{op_p:>8,.0f} vs {aa_p:>8,.0f}" if (op_p is not None and aa_p is not None) else "FAIL"
        s_str = f"{op_s:>4} vs {aa_s:<4}" if (op_s is not None and aa_s is not None) else "FAIL"
        veh_str = f"{op_veh:>3} vs {aa_veh:<3}" if (op_veh is not None and aa_veh is not None) else "FAIL"
        stn_str = f"{op_stn:>3} vs {aa_stn:<3}" if (op_stn is not None and aa_stn is not None) else "FAIL"

        print(f"{s:<8} | {v_str:<32} | {p_str:<28} | {s_str:<14} | {veh_str:<16} | {stn_str:<12}")

    print("-" * len(header))

    stats = payload["statistics"]
    for arm in ARMS:
        s = stats.get(arm, {})
        cv = s.get("company_value", {}).get("mean")
        py = s.get("profit_year", {}).get("mean")
        sc = s.get("performance_history", {}).get("mean")
        nv_list = [r["n_vehicles"] for r in summary if r["arm"] == arm and r.get("n_vehicles") is not None and r.get("run_ok", True)]
        ns_list = [r["n_stations"] for r in summary if r["arm"] == arm and r.get("n_stations") is not None and r.get("run_ok", True)]
        nv = statistics.mean(nv_list) if nv_list else None
        ns = statistics.mean(ns_list) if ns_list else None
        nv_str = f"{nv:>4.1f}" if nv is not None else " N/A"
        ns_str = f"{ns:>4.1f}" if ns is not None else " N/A"
        if cv is not None:
            print(f"MOYENNE [{arm:<8}] : CV: {cv:>10,.0f} £ | Profit/an: {py:>8,.0f} £ | Score: {sc:>4.0f} | Véhicules: {nv_str} | Gares: {ns_str}")

    print("\n=== COMPARAISON APPARIÉE OPEXAI vs AAAHOGEX ===")
    for comp in payload["paired_comparisons"]:
        a, b = comp["arm_a"], comp["arm_b"]
        if (a == "OpexAI" and b == "AAAHogEx") or (a == "AAAHogEx" and b == "OpexAI"):
            for metric in ("company_value", "profit_year", "performance_history", "median_station_rating"):
                m = comp["metrics"].get(metric, {})
                diff = m.get("mean_difference_percent")
                wins = m.get("arm_a_beats_arm_b")
                n = m.get("n")
                pval = m.get("wilcoxon_p") or m.get("sign_test_p")
                pval_str = f"p={pval:.4f}" if pval is not None else "p=N/A"
                if diff is not None:
                    print(f"  {metric:<24} : d% = {diff:+.2f}% | Victoires {a} = {wins}/{n} ({pval_str})")

    if failed:
        raise SystemExit(f"Banc invalide : {len(failed)} echec(s) NoAI")


def selftest():
    """Vérifie unitairement le comportement d'extract_company_record et de summarise en mode fail-closed."""
    # 1. Test sur fixture réelle
    fixture_path = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            c66 = json.load(f)
        rec0 = extract_company_record(c66["chunks"], 0, ["OpexAI", 42, 0], "1970-12-01")
        assert rec0["vehs_chunk_valid"] is True, "Chunk VEHS valide attendu"
        assert rec0["stnn_chunk_valid"] is True, "Chunk STNN valide attendu"
        assert rec0["n_vehicles"] == 26, f"26 entrées attendues, reçu {rec0['n_vehicles']}"
        assert rec0["primary_vehicles"] == 21, f"21 pilotables attendus, reçu {rec0['primary_vehicles']}"
        assert rec0["n_stations"] == 24, f"24 gares attendues, reçu {rec0['n_stations']}"

    # 2. Test fail-closed sur chunks manquants / invalides
    corrupt_chunks = {"VEHS": None, "STNN": None, "PLYR": {0: {"old_economy": []}}}
    rec_bad = extract_company_record(corrupt_chunks, 0, ["OpexAI", 99, 0], "1970-12-01")
    assert rec_bad["vehs_chunk_valid"] is False, "VEHS None doit être invalide"
    assert rec_bad["stnn_chunk_valid"] is False, "STNN None doit être invalide"
    assert rec_bad["n_vehicles"] is None, "n_vehicles doit être None sur chunk invalide"
    assert rec_bad["primary_vehicles"] is None, "primary_vehicles doit être None sur chunk invalide"
    assert rec_bad["n_stations"] is None, "n_stations doit être None sur chunk invalide"

    # 3. Test summarise sur row corrompue
    summary = summarise([rec_bad])
    assert len(summary) == 1
    s0 = summary[0]
    assert s0["run_ok"] is False, "Le run doit être marqué en échec (run_ok=False)"
    assert s0["physical_ok"] is False, "physical_ok doit être False"
    assert "physical_decode_failure" in s0["failure_reason"], f"failure_reason attendu, reçu: {s0['failure_reason']}"
    assert s0["n_vehicles"] is None, "n_vehicles doit rester None dans summary"
    print("Selftest bench_1v1_5y_20seeds.py réussi avec succès !")


if __name__ == "__main__":
    main()
