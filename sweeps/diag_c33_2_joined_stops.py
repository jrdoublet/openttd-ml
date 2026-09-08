"""Diagnostic C33.2 : Arrêts de rabattement joints au chantier de l'aéroport.

Compare :
- OpexAI (défaut : air_joined_stops=0)
- OpexAI[air_joined_stops=1] (C33.2 : arrêts joints dans le chantier aéroport)
- OpexAI[abandon_cooldown_days=365,abandon_gen_filter=1,air_joined_stops=1] (Combo C33.3 + C22 + C33.2)

Sur 5 graines x 6 ans standard.
"""
import argparse
from pathlib import Path
import sys

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

ARMS = (
    "OpexAI",
    "OpexAI[air_joined_stops=1]",
    "OpexAI[abandon_cooldown_days=365,abandon_gen_filter=1,air_joined_stops=1]",
)
SEEDS = (42, 100, 7, 999, 2026)
YEARS = 6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    out = args.out if args.out is not None else (
        ROOT / "results" / f"diag_c33_2_joined_stops_{args.years}y_{len(args.seeds)}seeds.json"
    )

    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
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
        experiments=experiments(built, list(args.seeds), args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    failed = [row for row in summary if not row["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": list(args.seeds),
        "arms": list(ARMS),
        "openttd_config": cfg,
        "defaults": "air_joined_stops=0",
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": [
            {"arm": row["arm"], "seed": row["seed"], "failure_reason": row["failure_reason"]}
            for row in failed
        ],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    for arm in ARMS:
        arm_rows = [row for row in summary if row["arm"] == arm]
        n = len(arm_rows) or 1

        def mean(key):
            return sum((row.get(key) or 0) for row in arm_rows) / n

        print(
            f"{arm:60} "
            f"val={mean('company_value'):,.0f} £ "
            f"profit_yr={mean('profit_year'):,.0f} £ "
            f"perf={mean('performance_history'):.1f} "
            f"st={mean('median_station_rating'):.1f} "
            f"vehs={mean('n_vehicles'):.1f} "
            f"stns={mean('n_stations'):.1f}"
        )


if __name__ == "__main__":
    main()
