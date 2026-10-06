#!/usr/bin/env python3
"""Diagnostic passif C121 cadence : reutilise C117 sur le baseline C121 courant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

import run_c117_air_throughput as c117
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from diag_c117_air_throughput import analyse


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=(42, 100))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "c121_cadence_c117_2x3_20261001_r1.json",
    )
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("--workers doit etre entre 1 et 4")

    enable_savegame_cleanup()
    settings = (
        ("save_full_state", 0),
        ("c115_air_c100_capital_replay", 1),
        ("c121_air_economics", 1),
        ("c121_catalog_incremental", 1),
        ("c121_catalog_air_first_year", 0),
        ("c121_air_decision_depth_economics", 0),
        ("c121_air_portfolio_depth_economics", 0),
        ("c121_air_portfolio_split_economics", 0),
        ("c121_air_observation_growth", 0),
        ("c121_fleet_stock_growth", 0),
        ("c121_territory_first", 0),
        ("c121_aaa_line", 0),
        ("c117_air_throughput_probe", 1),
        ("b9_air_demand_shadow", 0),
    )
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
    cfg = make_cfg(1970)
    experiments = [{
        "bench_context": "solo",
        "bench_arm": "OpexAI[C121-base,c117=1]",
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
        result_processor=c117.keep,
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
            failed.append({"seed": seed, "reason": "no_c117_events"})

    analysis = analyse(final_rows)
    payload = {
        "campaign_id": args.out.stem,
        "purpose": "Passive C121 cadence diagnostic using existing C117 throughput telemetry; no policy change",
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
        "rows": final_rows,
        "analysis": analysis,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "health": payload["health"],
        "event_count": analysis.get("event_count"),
        "line_count": analysis.get("line_count"),
        "ramp": analysis.get("ramp"),
        "out": str(args.out),
    }, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
