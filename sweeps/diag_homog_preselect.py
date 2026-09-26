"""Diagnostic harness and extractor for homogeneous_preselect solo runs.

Extracts:
- C50_CHRONO phase=project_built (mode, rank in portfolio, line, cost, profit, roi)
- C50_CHRONO phase=fleet_built (mode, line, added, total)
- C78_BUILD (mode, rank, outcome, reason, P, C)
Under probe_portfolio=1 and probe_events=1.
Aggregates physical lines built by mode, vehicles by mode, and economic performance.
Documents existing probe limitations (absence of modal top-K rank, candidate fundScore, and overlap).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

OPEX_LINE_RE = re.compile(r"OPEX ((\d{4})-(\d{1,2})-(\d{1,2})) ([A-Z0-9_]+)\s*(.*)")


def parse_fields(rest: str) -> dict[str, str]:
    fields = {}
    for token in rest.split():
        if "=" in token:
            k, v = token.split("=", 1)
            fields[k] = v
    return fields


def to_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def to_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def extract_events(output: str) -> list[dict]:
    events = []
    for line in (output or "").splitlines():
        m = OPEX_LINE_RE.search(line)
        if not m:
            continue
        date_str, y, mo, d, tag, rest = m.groups()
        f = parse_fields(rest)
        if tag == "C50_CHRONO":
            phase = f.get("phase")
            if phase == "project_built":
                events.append({
                    "date": date_str,
                    "type": "project_built",
                    "mode": f.get("mode", "unknown"),
                    "rank": to_int(f.get("rank"), -1),
                    "line": to_int(f.get("line"), -1),
                    "cost": to_int(f.get("cost"), 0),
                    "profit": to_int(f.get("profit"), 0),
                    "roi": to_float(f.get("roi"), 0.0),
                    "cash_after": to_int(f.get("cash_after"), 0),
                    "available": to_int(f.get("available"), 0),
                })
            elif phase == "fleet_built":
                events.append({
                    "date": date_str,
                    "type": "fleet_built",
                    "mode": f.get("mode", "unknown"),
                    "line": to_int(f.get("line"), -1),
                    "added": to_int(f.get("added"), 0),
                    "total": to_int(f.get("total"), 0),
                    "cash_after": to_int(f.get("cash_after"), 0),
                })
            elif phase == "refused_cash":
                events.append({
                    "date": date_str,
                    "type": "refused_cash",
                    "mode": f.get("mode", "unknown"),
                    "rank": to_int(f.get("rank"), -1),
                    "cost": to_int(f.get("cost"), 0),
                    "profit": to_int(f.get("profit"), 0),
                    "roi": to_float(f.get("roi"), 0.0),
                })
        elif tag == "C78_BUILD":
            events.append({
                "date": date_str,
                "type": "c78_build",
                "year": to_int(f.get("year")),
                "rank": to_int(f.get("rank"), -1),
                "mode": f.get("mode", "unknown"),
                "outcome": f.get("outcome", "unknown"),
                "reason": f.get("reason", "unknown"),
                "P": to_int(f.get("P"), 0),
                "C": to_int(f.get("C"), 0),
            })
    return events


def analyze_diagnostics(events: list[dict], summary_rec: dict | None = None) -> dict:
    built_projects = [e for e in events if e["type"] == "project_built"]
    fleet_events = [e for e in events if e["type"] == "fleet_built"]

    lines_built_by_mode = {
        "air": 0,
        "rail": 0,
        "road": 0,
        "water": 0,
        "fleet": 0,
    }
    for e in built_projects:
        m = e.get("mode", "unknown")
        lines_built_by_mode[m] = lines_built_by_mode.get(m, 0) + 1

    fleet_additions_by_mode = {"air": 0, "rail": 0, "road": 0}
    for e in fleet_events:
        m = e.get("mode", "unknown")
        fleet_additions_by_mode[m] = fleet_additions_by_mode.get(m, 0) + 1

    rail_built = [e for e in built_projects if e["mode"] == "rail"]
    road_built = [e for e in built_projects if e["mode"] == "road"]
    air_built = [e for e in built_projects if e["mode"] == "air"]

    rec = summary_rec or {}
    primary_vehicles = rec.get("primary_vehicles_by_mode", {})

    return {
        "lines_built_by_mode": lines_built_by_mode,
        "fleet_additions_by_mode": fleet_additions_by_mode,
        "primary_vehicles_by_mode": primary_vehicles,
        "rail_projects_built": [
            {
                "line": e["line"],
                "rank_in_portfolio": e["rank"],
                "cost": e["cost"],
                "profit": e["profit"],
                "roi": e["roi"],
                "date": e["date"],
            }
            for e in rail_built
        ],
        "road_projects_built": [
            {
                "line": e["line"],
                "rank_in_portfolio": e["rank"],
                "cost": e["cost"],
                "profit": e["profit"],
                "roi": e["roi"],
                "date": e["date"],
            }
            for e in road_built
        ],
        "probe_limitations": {
            "candidate_fund_score": (
                "Non exposé par les sondes Squirrel actuelles. "
                "C50_CHRONO expose cost, profit, roi ; fundScore n'est pas loggé."
            ),
            "modal_top_k_rank": (
                "Non exposé par les sondes Squirrel actuelles. "
                "Le rang loggé dans C50_CHRONO est l'indice dans le portefeuille unifié "
                "(this._projects.best), pas le rang dans le top-K de chaque mode."
            ),
            "top_k_overlap": (
                "Non exposé par les sondes Squirrel actuelles. "
                "Aucune sonde ne journalise l'ensemble des candidats admis ou les top-K modaux."
            ),
        },
        "company_value": rec.get("company_value"),
        "profit_year": rec.get("profit_year"),
        "performance_history": rec.get("performance_history"),
        "n_stations": rec.get("n_stations"),
        "n_vehicles": rec.get("n_vehicles"),
        "stations_by_facility": rec.get("stations_by_facility", {}),
    }


def main():
    import openttdlab
    from openttdlab import bananas_ai_library, run_experiments
    import bench_v2
    from bench_v2 import (
        OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
        experiments, keep, summarise, write_json_atomically,
    )

    real_check_output = openttdlab.subprocess.check_output

    def check_output_with_script_debug(args, *rest, **kwargs):
        args = tuple(args)
        if any(str(arg).startswith("-vnull") for arg in args):
            args = args[:1] + ("-d", "script=4") + args[1:]
        return real_check_output(args, *rest, **kwargs)

    openttdlab.subprocess.check_output = check_output_with_script_debug

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 999, 5678])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    bench_v2.CHECKPOINT_PATH = Path("/dev/null")
    enable_savegame_cleanup()
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
    results = []
    for rec in summary:
        evs = extract_events(rec.get("openttd_output", ""))
        diag = analyze_diagnostics(evs, rec)
        results.append({
            "arm": rec["arm"],
            "seed": rec["seed"],
            "run_ok": rec.get("run_ok", False),
            "diagnostics": diag,
        })
    write_json_atomically(Path(args.out), {
        "arms": args.arms,
        "seeds": args.seeds,
        "years": args.years,
        "results": results,
    })
    print(f"Done: {args.out}")


if __name__ == "__main__":
    main()
