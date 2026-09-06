"""Banc officiel 20x10 du correctif pax voirie. 2x2 overlap x voirie.

Sans script=4. keep() rend un tuple.
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
    SEEDS as CANONICAL_SEEDS,
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
    "OpexAI[road_pax_overlap=0,road_pax_voirie=0]",
    "OpexAI[road_pax_overlap=1,road_pax_voirie=0]",
    "OpexAI[road_pax_overlap=0,road_pax_voirie=1]",
    "OpexAI[road_pax_overlap=1,road_pax_voirie=1]",
)
SEEDS = CANONICAL_SEEDS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    out = args.out if args.out is not None else (
        ROOT / "docs" / f"bench_voirie_fix_{args.years}y_{len(args.seeds)}seeds.json"
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
    failed = [r for r in summary if not r["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": list(args.seeds),
        "arms": list(ARMS),
        "openttd_config": cfg,
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": [
            {"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]}
            for r in failed
        ],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    for arm in ARMS:
        rows_a = [r for r in summary if r["arm"] == arm]
        if not rows_a:
            continue
        def mean(k):
            return sum((r.get(k) or 0) for r in rows_a) / len(rows_a)
        print(f"  {arm}: n={len(rows_a)} profit={mean('profit_year'):.0f} "
              f"score={mean('performance_history'):.0f} notes={mean('median_station_rating'):.1f} "
              f"value={mean('company_value'):.0f} veh={mean('n_vehicles'):.1f} "
              f"stn={mean('n_stations'):.1f}")
    for cmp_ in payload["paired_comparisons"]:
        print(f"-- {cmp_['arm_a']} vs {cmp_['arm_b']} --")
        for metric, m in cmp_["metrics"].items():
            print(f"   {metric}: d%={m.get('mean_difference_percent')} "
                  f"wins={m.get('arm_a_beats_arm_b')}/{m.get('n')}")


if __name__ == "__main__":
    main()
