#!/usr/bin/env python3
"""Diagnostic V88 : enquête complète sur l'impact des chaînes de biens sur la flotte aérienne.

Ce script exécute des parties solo de 6 ans avec -d script=4 sous OpenTTDLab,
et extrait la chronologie complète et détaillée :
- C78_SLOT (projects_pass, air_attempt, air_outcome, pass_stop, projects_exit)
- C50_CHRONO (project_built, fleet_built, refused_cash)
- CHAIN_* (chosen, step1_search, step1, step2_search, step2, wait, fail, delivery)
- C49_SCARCITY (arrêts de passe annuels)
- Séries mensuelles (avions, trains, route, caisse, profit, dépenses)
"""
import argparse
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab
from openttdlab import bananas_ai_library, run_experiments
import bench_v2
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_LINE_RE = re.compile(r"OPEX ((\d{4})-\d{1,2}-\d{1,2}) ([A-Z0-9_]+)\s*(.*)")


def parse_fields(fields_str):
    res = {}
    for token in fields_str.split():
        if "=" in token:
            k, v = token.split("=", 1)
            res[k] = v
    return res


def analyze_game_output(output, rows_series):
    """Analyse exhaustive des journaux stdout d'une partie."""
    monthly_series = []
    for r in rows_series:
        by_mode = r.get("primary_vehicles_by_mode") or {}
        monthly_series.append({
            "date": str(r.get("date")),
            "air": by_mode.get("air", 0),
            "rail": by_mode.get("rail", 0),
            "road": by_mode.get("road", 0),
            "total_vehs": r.get("primary_vehicles", 0),
            "money": r.get("money"),
            "profit_year": r.get("profit_year"),
            "income_last_year": r.get("income_last_year"),
            "expenses_last_year": r.get("expenses_last_year"),
            "company_value": r.get("company_value"),
        })

    chain_events = []
    c78_projects_pass = []
    c78_air_attempts = []
    c78_air_outcomes = []
    c78_pass_stops = []
    c78_projects_exit = []
    c50_builds = []
    c50_fleet_builds = []
    c50_cash_refusals = []
    c49_annual = []

    for line in (output or "").splitlines():
        m = OPEX_LINE_RE.search(line)
        if not m:
            continue
        date_str, year_str, tag, rest = m.groups()
        year = int(year_str)

        if tag.startswith("CHAIN_"):
            chain_events.append({
                "date": date_str, "year": year, "tag": tag, "fields": parse_fields(rest), "raw": rest.strip()
            })
        elif tag == "C78_SLOT":
            fields = parse_fields(rest)
            phase = fields.get("phase")
            if phase == "projects_pass":
                c78_projects_pass.append({"date": date_str, "year": year, **fields})
            elif phase == "air_attempt":
                c78_air_attempts.append({"date": date_str, "year": year, **fields})
            elif phase == "air_outcome":
                c78_air_outcomes.append({"date": date_str, "year": year, **fields})
            elif phase == "pass_stop":
                c78_pass_stops.append({"date": date_str, "year": year, **fields})
            elif phase == "projects_exit":
                c78_projects_exit.append({"date": date_str, "year": year, **fields})
        elif tag == "C50_CHRONO":
            fields = parse_fields(rest)
            phase = fields.get("phase")
            if phase == "project_built":
                c50_builds.append({"date": date_str, "year": year, **fields})
            elif phase == "fleet_built":
                c50_fleet_builds.append({"date": date_str, "year": year, **fields})
            elif phase == "refused_cash":
                c50_cash_refusals.append({"date": date_str, "year": year, **fields})
        elif tag == "C49_SCARCITY":
            fields = parse_fields(rest)
            if fields.get("phase") == "annual":
                c49_annual.append({"date": date_str, "year": year, **fields})

    # Synthèse annuelle du capital dépensé par mode
    spend_by_year_mode = {}
    for b in c50_builds:
        yr = b["year"]
        mode = b.get("mode", "unknown")
        cost = int(b.get("cost", 0))
        spend_by_year_mode.setdefault(yr, {}).setdefault(mode, 0)
        spend_by_year_mode[yr][mode] += cost

    # Synthèse annuelle des véhicules ajoutés via fleet
    fleet_added_by_year_mode = {}
    for fb in c50_fleet_builds:
        yr = fb["year"]
        mode = fb.get("mode", "unknown")
        added = int(fb.get("added", 0))
        fleet_added_by_year_mode.setdefault(yr, {}).setdefault(mode, 0)
        fleet_added_by_year_mode[yr][mode] += added

    return {
        "monthly_series": monthly_series,
        "chain_events": chain_events,
        "c78_projects_pass": c78_projects_pass,
        "c78_air_attempts": c78_air_attempts,
        "c78_air_outcomes": c78_air_outcomes,
        "c78_pass_stops": c78_pass_stops,
        "c78_projects_exit": c78_projects_exit,
        "c50_builds": c50_builds,
        "c50_fleet_builds": c50_fleet_builds,
        "c50_cash_refusals": c50_cash_refusals,
        "c49_annual": c49_annual,
        "spend_by_year_mode": spend_by_year_mode,
        "fleet_added_by_year_mode": fleet_added_by_year_mode,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[5678, 999, 100])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--raw-events", type=Path, default=None)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = Path("/dev/null")
    enable_savegame_cleanup()

    print(f"Launching {len(args.arms)} arms x {len(args.seeds)} seeds x {args.years} years...")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms(args.arms), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    summary = summarise(rows, expected_last_year=1970 + args.years - 1, expected_savegames=args.years * 12)

    grouped_rows = {}
    for r in rows:
        key = (r["run"][0], r["run"][1])
        grouped_rows.setdefault(key, []).append(r)

    results = []
    if args.raw_events:
        raw_fh = open(args.raw_events, "w")
    else:
        raw_fh = None

    for rec in summary:
        arm = rec["arm"]
        seed = rec["seed"]
        series = grouped_rows.get((arm, seed), [])
        output = rec.get("openttd_output", "")

        analysis = analyze_game_output(output, series)

        if raw_fh:
            for ce in analysis["chain_events"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "chain", **ce}) + "\n")
            for ps in analysis["c78_pass_stops"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "pass_stop", **ps}) + "\n")
            for b in analysis["c50_builds"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "project_built", **b}) + "\n")
            for fb in analysis["c50_fleet_builds"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "fleet_built", **fb}) + "\n")
            for cr in analysis["c50_cash_refusals"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "cash_refusal", **cr}) + "\n")
            for att in analysis["c78_air_attempts"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "air_attempt", **att}) + "\n")
            for out_ev in analysis["c78_air_outcomes"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "air_outcome", **out_ev}) + "\n")
            for pe in analysis["c78_projects_exit"]:
                raw_fh.write(json.dumps({"arm": arm, "seed": seed, "type": "projects_exit", **pe}) + "\n")

        results.append({
            "arm": arm,
            "seed": seed,
            "run_ok": rec["run_ok"],
            "company_value": rec.get("company_value"),
            "profit_year": rec.get("profit_year"),
            "primary_vehicles": rec.get("primary_vehicles"),
            "primary_vehicles_by_mode": rec.get("primary_vehicles_by_mode"),
            "analysis": analysis,
        })

    if raw_fh:
        raw_fh.close()

    write_json_atomically(out, {
        "arms": args.arms,
        "seeds": args.seeds,
        "years": args.years,
        "results": results,
    })
    print(f"Done! Results written to {out}")


if __name__ == "__main__":
    main()
