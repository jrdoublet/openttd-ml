"""Diagnostic solo C80 Étape 1 : impact de la porte d'éligibilité rail passive sur les passes projects.

Extrait :
- C56_TASK TASK_ENTER name=projects (sous probe_events)
- C56_TASK RAIL_SEARCH_START / RAIL_SEARCH_END
- C78_SLOT projects_pass / pass_stop (reason=rail_search etc.)
- C50_CHRONO phase=project_built
- C78_BUILD (outcome, reason)
Calcule les grandeurs physiques : passes projects, intervalle médian (global, pendant/hors A*),
arrêts rail_search, constructions par mode, avions, profit_year, company_value.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

OPEX_LINE_RE = re.compile(r"OPEX ((\d{4})-(\d{1,2})-(\d{1,2})) ([A-Z0-9_]+)\s*(.*)")
KEEP_C56 = (
    "RAIL_SEARCH_START", "RAIL_SEARCH_END",
    "RAIL_STOCK_START", "RAIL_STOCK_DEPOSIT", "RAIL_STOCK_TIMEOUT",
    "RAIL_STOCK_EXPIRE", "RAIL_STOCK_CONSUME", "RAIL_STOCK_REVALIDATE_FAIL",
    "RAIL_STOCK_SELECT",
)


def fields_of(rest):
    out = {}
    for token in rest.split():
        if "=" in token:
            k, v = token.split("=", 1)
            out[k] = v
    return out


def extract(output):
    events = []
    for line in (output or "").splitlines():
        m = OPEX_LINE_RE.search(line)
        if not m:
            continue
        date, _, _, _, tag, rest = m.groups()
        if tag == "C56_TASK":
            parts = rest.split(None, 1)
            kind = parts[0] if parts else ""
            f = fields_of(parts[1] if len(parts) > 1 else "")
            if kind == "TASK_ENTER" and f.get("name") == "projects":
                events.append({"date": date, "type": "projects_enter", "tick": f.get("tick")})
            elif kind in KEEP_C56:
                events.append({"date": date, "type": kind.lower(), **f})
        elif tag == "C78_SLOT":
            f = fields_of(rest)
            if f.get("phase") in ("projects_pass", "pass_stop"):
                events.append({"date": date, "type": "c78_" + f["phase"], **f})
        elif tag == "C50_CHRONO":
            f = fields_of(rest)
            if f.get("phase") == "project_built":
                events.append({"date": date, "type": "project_built", **f})
        elif tag == "C78_BUILD":
            f = fields_of(rest)
            events.append({"date": date, "type": "c78_build", **f})
    return events


def parse_date(d_str):
    y, m, d = map(int, d_str.split("-"))
    return datetime.date(y, m, d)


def analyze_events(events):
    astars = []
    cur_start = None
    for e in events:
        if e["type"] == "rail_search_start":
            cur_start = parse_date(e["date"])
        elif e["type"] == "rail_search_end" and cur_start:
            astars.append((cur_start, parse_date(e["date"])))
            cur_start = None
    if cur_start:
        astars.append((cur_start, datetime.date(2000, 1, 1)))

    enters = [e for e in events if e["type"] == "projects_enter"]
    dates = [parse_date(e["date"]) for e in enters]
    gaps_all = sorted([(dates[i] - dates[i-1]).days for i in range(1, len(dates))])
    gaps_in = []
    gaps_out = []
    for i in range(1, len(dates)):
        d = dates[i]
        in_astar = any(s <= d <= end for s, end in astars)
        gap = (dates[i] - dates[i-1]).days
        if in_astar:
            gaps_in.append(gap)
        else:
            gaps_out.append(gap)
    gaps_in.sort()
    gaps_out.sort()

    med_all = gaps_all[len(gaps_all) // 2] if gaps_all else None
    med_in = gaps_in[len(gaps_in) // 2] if gaps_in else None
    med_out = gaps_out[len(gaps_out) // 2] if gaps_out else None

    rail_search_stops = len([
        e for e in events
        if e["type"] == "c78_pass_stop" and e.get("reason") == "rail_search"
    ])
    no_ready_route_discards = len([
        e for e in events
        if e["type"] == "c78_build" and e.get("reason") == "no_ready_route"
    ])

    builds_by_mode = {}
    for e in events:
        if e["type"] == "project_built":
            m = e.get("mode", "unknown")
            builds_by_mode[m] = builds_by_mode.get(m, 0) + 1

    # Métriques C80 Stock & Worker
    stock_deposits = [e for e in events if e["type"] == "rail_stock_deposit"]
    stock_consumes = [e for e in events if e["type"] == "rail_stock_consume"]
    stock_expires = [e for e in events if e["type"] == "rail_stock_expire"]
    stock_timeouts = [e for e in events if e["type"] == "rail_stock_timeout"]
    stock_reval_fails = [e for e in events if e["type"] == "rail_stock_revalidate_fail"]
    stock_selections = [e for e in events if e["type"] == "rail_stock_select"]
    def _number(e, key):
        try:
            return int(e.get(key, 0))
        except (TypeError, ValueError):
            return 0
    stock_ready_passes = sum(_number(e, "ready") > 0 for e in stock_selections)
    stock_funded_passes = sum(_number(e, "funded") > 0 for e in stock_selections)
    stock_merge_ops = [_number(e, "merge_ops") for e in stock_selections]

    search_days_list = []
    for e in stock_deposits + stock_timeouts:
        if "days" in e and e["days"] is not None:
            try:
                search_days_list.append(int(e["days"]))
            except (ValueError, TypeError):
                pass
    search_days_list.sort()
    search_days_med = search_days_list[len(search_days_list) // 2] if search_days_list else None
    search_days_max = max(search_days_list) if search_days_list else None

    delay_days_list = []
    for e in stock_consumes:
        if "delay_days" in e and e["delay_days"] is not None:
            try:
                delay_days_list.append(int(e["delay_days"]))
            except (ValueError, TypeError):
                pass
    delay_days_list.sort()
    delay_days_med = delay_days_list[len(delay_days_list) // 2] if delay_days_list else None
    delay_days_max = max(delay_days_list) if delay_days_list else None

    return {
        "passes_projects": len(enters),
        "median_gap_days": med_all,
        "median_gap_in_astar": med_in,
        "n_gaps_in_astar": len(gaps_in),
        "median_gap_out_astar": med_out,
        "n_gaps_out_astar": len(gaps_out),
        "rail_search_stops": rail_search_stops,
        "no_ready_route_discards": no_ready_route_discards,
        "builds_by_mode": builds_by_mode,
        "stock_deposits": len(stock_deposits),
        "stock_consumes": len(stock_consumes),
        "stock_expires": len(stock_expires),
        "stock_timeouts": len(stock_timeouts),
        "stock_reval_fails": len(stock_reval_fails),
        "stock_ready_passes": stock_ready_passes,
        "stock_funded_passes": stock_funded_passes,
        "stock_built": len(stock_consumes),
        "stock_merge_ops": stock_merge_ops,
        "search_days_median": search_days_med,
        "search_days_max": search_days_max,
        "delay_days_median": delay_days_med,
        "delay_days_max": delay_days_max,
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
        evs = extract(rec.get("openttd_output", ""))
        metrics = analyze_events(evs)
        results.append({
            "arm": rec["arm"],
            "seed": rec["seed"],
            "run_ok": rec["run_ok"],
            "company_value": rec.get("company_value"),
            "profit_year": rec.get("profit_year"),
            "primary_vehicles_by_mode": rec.get("primary_vehicles_by_mode"),
            "metrics": metrics,
            "events": evs,
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
