"""Banc apparie : air_portfolio + air_cheap_site=1 + portfolio_max_batch=3 contre le defaut.

Témoin : OpexAI (air_portfolio=1 deja par defaut C36.2, batch=1, cheap=0).
Test   : OpexAI[air_portfolio=1,air_cheap_site=1,portfolio_max_batch=3].

Sans script=4 : c'est un banc de valeur (HOL batch), pas de sondes FindSite.
keep() rend un tuple. Lecture PLYR.old_economy.
"""
import argparse
import json
import sys
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENTTD_VERSION,
    OPENGFX_VERSION,
    SUCCESS_METRICS,
    arm_statistics,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    make_cfg,
    paired_comparisons,
    summarise,
    write_json_atomically,
)
import bench_v2

SEEDS = (42, 100, 7, 999, 2026, 1, 17, 73, 314, 512)
ARMS = (
    "OpexAI",
    "OpexAI[air_portfolio=1,air_cheap_site=1,portfolio_max_batch=3]",
)
YEARS = 3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    seeds = tuple(args.seeds) if args.seeds else SEEDS
    if args.out is None:
        tag = "10seeds" if args.seeds is None else "s" + "-".join(str(s) for s in seeds)
        args.out = ROOT / "docs" / f"bench_c36_3_cheap_batch3_{args.years}y_{tag}.json"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(list(ARMS))
    cfg = make_cfg(1970)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built, list(seeds), args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    failed = [r for r in summary if not r["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "starting_year": 1970,
        "seeds": list(seeds),
        "arms": list(ARMS),
        "repeats": 1,
        "openttd_config": cfg,
        "metric": (
            "PLYR[0].old_economy[0] : company_value, performance_history, "
            "profit, profit_year ; STNN median_station_rating"
        ),
        "success_metrics": list(SUCCESS_METRICS),
        "paired_reading": "mean(A(seed) - B(seed))",
        "checkpoint": str(bench_v2.CHECKPOINT_PATH),
        "summary": summary,
        "failed_runs": [
            {"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]}
            for r in failed
        ],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(args.out, payload)
    print(json.dumps({
        "out": str(args.out),
        "failed": len(failed),
        "paired": payload["paired_comparisons"],
        "rows": [
            {
                "arm": r["arm"],
                "seed": r["seed"],
                "company_value": r["company_value"],
                "profit_year": r["profit_year"],
                "performance_history": r["performance_history"],
                "n_vehicles": r["n_vehicles"],
                "n_stations": r["n_stations"],
                "run_ok": r["run_ok"],
            }
            for r in summary
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
