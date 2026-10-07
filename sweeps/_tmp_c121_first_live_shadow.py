#!/usr/bin/env python3
"""Passive C121 first 1->2 live-evidence shadow using existing C117 sampling."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re

from openttdlab import bananas_ai_library, local_folder, run_experiments

import run_c117_air_throughput as c117  # installs script=4 capture and parse helpers
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"C121_FIRST_LIVE\s+(.*)")


def keep(row):
    experiment = row.get("experiment", {})
    seed = experiment.get("seed")
    date_s = str(row.get("date", ""))
    days = int(experiment.get("days", 0) or 0)
    final_date = date(1970, 1, 1) + timedelta(days=days)
    try:
        row_date = date.fromisoformat(date_s[:10])
    except ValueError:
        return ()
    if row_date < final_date - timedelta(days=31) or row_date > final_date:
        return ()
    output = row.get("output", "") or ""
    events = [c117.parse_fields(fields) for fields in TAG_RE.findall(output)]
    return ({
        "seed": seed,
        "date": date_s,
        "events": events,
        "event_count": len(events),
        "had_script_error": "Script died unexpectedly" in output or "SCRIPT ERROR" in output,
    },)


def summarize(rows):
    events = []
    for row in rows:
        seed = row.get("seed")
        for raw in row.get("events", []):
            e = dict(raw)
            e["seed"] = seed
            events.append(e)
    lines = {(e.get("seed"), e.get("line")) for e in events if e.get("line") is not None}
    out = {"events": len(events), "lines": len(lines)}
    for key in ("rule_bal60", "rule_bal90", "rule_strict90", "rule_dual90"):
        first = {}
        for e in events:
            if int(e.get(key, 0) or 0) != 1:
                continue
            ident = (e.get("seed"), e.get("line"))
            age = int(e.get("age_days", -1) or -1)
            if ident not in first or age < first[ident]:
                first[ident] = age
        ages = sorted(first.values())
        out[key] = {
            "lines": len(ages),
            "age_min": ages[0] if ages else None,
            "age_median": ages[len(ages) // 2] if ages else None,
            "age_max": ages[-1] if ages else None,
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=(42, 100))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "c121_first_live_shadow_2x3_20261001_r1.json",
    )
    args = parser.parse_args()
    if not 1 <= args.workers <= 5:
        parser.error("--workers doit etre entre 1 et 5")

    enable_savegame_cleanup()
    settings = (
        ("save_full_state", 0),
        ("c115_air_c100_capital_replay", 1),
        ("c121_air_economics", 1),
        ("c121_catalog_incremental", 1),
        ("c121_catalog_air_first_year", 0),
        ("c121_air_observation_growth", 0),
        ("c121_air_first_observation_growth", 0),
        ("c121_fleet_stock_growth", 0),
        ("c121_territory_first", 0),
        ("c121_aaa_line", 0),
        ("c117_air_throughput_probe", 0),
        ("c121_air_first_live_shadow", 1),
        ("b9_air_demand_shadow", 0),
    )
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
    cfg = make_cfg(1970)
    experiments = [{
        "bench_context": "solo",
        "bench_arm": "OpexAI[C121-base,first-live-shadow=1]",
        "seed": seed,
        "days": 365 * args.years,
        "openttd_config": cfg,
        "ais": (opex,),
    } for seed in args.seeds]

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
    latest = {}
    for row in rows:
        seed = row.get("seed")
        if seed is not None and (seed not in latest or row.get("date", "") > latest[seed].get("date", "")):
            latest[seed] = row
    final_rows = [latest[seed] for seed in args.seeds if seed in latest]
    failed = []
    for seed in args.seeds:
        row = latest.get(seed)
        if row is None:
            failed.append({"seed": seed, "reason": "missing"})
        elif row.get("had_script_error"):
            failed.append({"seed": seed, "reason": "script_error"})
        elif row.get("event_count", 0) <= 0:
            failed.append({"seed": seed, "reason": "no_shadow_events"})
    summary = summarize(final_rows)
    payload = {
        "campaign_id": args.out.stem,
        "purpose": "Passive C121 first 1->2 live-evidence shadow; no policy change",
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "settings": dict(settings),
        "health": {
            "expected_runs": len(args.seeds),
            "observed_runs": len(final_rows),
            "failed_runs": failed,
            "all_runs_healthy": len(final_rows) == len(args.seeds) and not failed,
        },
        "summary": summary,
        "rows": final_rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"health": payload["health"], "summary": summary, "out": str(args.out)}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
