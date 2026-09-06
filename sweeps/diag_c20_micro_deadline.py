"""Diagnostic C20 : Échéance par micro-étape pour la recherche ferroviaire reprenable.

Compare :
- OpexAI (défaut : rail_search_resumable=0, mode bloquant)
- OpexAI[rail_search_resumable=1] (A4 historique : échéance globale en ticks posée une fois)
- OpexAI[rail_search_resumable=1,rail_micro_deadline=1] (C20 : échéance locale renouvelée par tranche)

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
    "OpexAI[rail_search_resumable=1]",
    "OpexAI[rail_search_resumable=1,rail_micro_deadline=1]",
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
        ROOT / "docs" / f"diag_c20_micro_deadline_{args.years}y_{len(args.seeds)}seeds.json"
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
        "defaults": "rail_search_resumable=0,rail_micro_deadline=0",
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
            f"  {arm}: n={len(arm_rows)} profit={mean('profit_year'):.0f} "
            f"score={mean('performance_history'):.0f} notes={mean('median_station_rating'):.1f} "
            f"value={mean('company_value'):.0f} veh={mean('n_vehicles'):.1f} "
            f"stn={mean('n_stations'):.1f}"
        )
    for comparison in payload["paired_comparisons"]:
        print(f"-- {comparison['arm_a']} vs {comparison['arm_b']} --")
        for metric, values in comparison["metrics"].items():
            print(
                f"   {metric}: d%={values.get('mean_difference_percent')} "
                f"wins={values.get('arm_a_beats_arm_b')}/{values.get('n')}"
            )


if __name__ == "__main__":
    main()
