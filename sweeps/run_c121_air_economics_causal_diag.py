#!/usr/bin/env python3
"""C121 causal : diagnostic solo avec logs script=4 et telemetry C121_BUILD."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from openttdlab import local_folder, run_experiments

import run_c121_air_economics_shadow as base
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=(42,))
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--causal", type=int, choices=(0, 1), default=1)
    parser.add_argument("--duel", action="store_true")
    parser.add_argument("--throughput-probe", type=int, choices=(0, 1), default=1)
    parser.add_argument("--out", type=Path,
        default=ROOT / "results" / "diag_c121_causal_seed42_2y_20260928.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")

    enable_savegame_cleanup()
    settings = (
        ("save_full_state", 0),
        ("c115_air_c100_capital_replay", 1),
        ("c117_air_throughput_probe", args.throughput_probe),
        ("c121_air_economics_shadow", 0),
        ("c121_air_economics", args.causal),
        ("c121_air_engine_replay_shadow", 0),
        ("b9_air_demand_shadow", 0),
    )
    with base.opex_source_for_shadow() as opex_source:
        opex = local_folder(str(opex_source), "OpexAI", settings)
        hogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ()) if args.duel else None
        cfg = make_cfg(1970)
        experiments = [{
            "bench_context": "duel" if args.duel else "solo",
            "bench_arm": f"OpexAI[C115=1,C121-causal={args.causal}]",
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex, hogex) if args.duel else (opex,),
        } for seed in args.seeds]
        processor_module = importlib.import_module("run_c121_air_economics_shadow")
        processor_module.LINE_TELEMETRY = False
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=experiments,
            max_workers=args.workers,
            result_processor=processor_module.keep,
            ai_libraries=(
                base.cached_bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                base.cached_bananas_ai_library("5046524c", "Pathfinder.Rail"),
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
    payload = {
        "campaign_id": args.out.stem,
        "purpose": "C121 causal diagnostic; script=4; opcode/cold-start telemetry",
        "years": args.years, "seeds": args.seeds, "workers": args.workers,
        "duel": args.duel, "throughput_probe": args.throughput_probe,
        "settings": dict(settings),
        "health": {"expected_runs": len(args.seeds), "observed_runs": len(final_rows),
            "failed_runs": failed, "all_runs_healthy": len(final_rows) == len(args.seeds) and not failed},
        "rows": final_rows, "analysis": base.analyse(final_rows),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"health": payload["health"],
        "c121_builds": sum(row.get("c121_build_count", 0) for row in final_rows),
        "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
