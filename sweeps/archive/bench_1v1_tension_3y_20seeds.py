"""Banc 1v1 apparié : AAAHogEx vs OpexAI (défaut) vs OpexAI[tension_scoring=1].

Horizon : 3 ans (standard 1v1 contre AAAHogEx), 20 graines canoniques, départ 1970.
Mesure : Company Value, Profit Annuel, Performance History, Median Station Rating, Véhicules, Gares.
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
    SEEDS as CANONICAL_SEEDS,
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

ARMS = ("AAAHogEx", "OpexAI", "OpexAI[tension_scoring=1]")
YEARS = 3
STARTING_YEAR = 1970


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()

    seeds = tuple(args.seeds) if args.seeds else CANONICAL_SEEDS
    out = args.out if args.out is not None else (
        ROOT / "results" / f"bench_1v1_{args.years}y_tension_{len(seeds)}seeds.json"
    )

    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    built = build_arms(list(ARMS))
    cfg = make_cfg(STARTING_YEAR)

    print(f"=== Lancement Banc 1v1 : {len(ARMS)} arms x {len(seeds)} graines x {args.years} ans ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built, list(seeds), args.years, 1, STARTING_YEAR),
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
        "starting_year": STARTING_YEAR,
        "seeds": list(seeds),
        "arms": list(ARMS),
        "openttd_config": cfg,
        "defaults": "air_cheap_site=1,road_pax_overlap=1,road_pax_voirie=1",
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

    print("\n" + "=" * 105)
    print(f"BANC 1v1 AAAHOGEX vs OPEXAI (AVEC ET SANS TENSION SCORING) — {args.years} ANS ({len(seeds)} GRAINES)")
    print("=" * 105)

    for arm in ARMS:
        arm_rows = [row for row in summary if row["arm"] == arm]
        n = len(arm_rows) or 1

        def mean(key):
            return sum((row.get(key) or 0) for row in arm_rows) / n

        print(
            f"  {arm:<35}: n={len(arm_rows)} profit={mean('profit_year'):10.0f} "
            f"score={mean('performance_history'):5.0f} notes={mean('median_station_rating'):5.1f} "
            f"value={mean('company_value'):10.0f} veh={mean('n_vehicles'):5.1f} "
            f"stn={mean('n_stations'):5.1f}"
        )

    print("\n" + "-" * 105)
    print("COMPARAISONS APPARIÉES (A vs B) :")
    print("-" * 105)
    for comp in payload["paired_comparisons"]:
        a = comp["arm_a"]
        b = comp["arm_b"]
        print(f"\n-- {a} vs {b} --")
        for metric in ("profit_year", "performance_history", "median_station_rating", "company_value"):
            values = comp["metrics"].get(metric, {})
            diff_pct = values.get("mean_difference_percent")
            wins_a = values.get("arm_a_beats_arm_b")
            n = values.get("n")
            print(f"   {metric:<24}: d%={diff_pct:7.2f}% ({a} gagne {wins_a}/{n})")


if __name__ == "__main__":
    main()
