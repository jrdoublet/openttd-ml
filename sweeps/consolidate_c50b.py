"""Consolide la campagne C50b reprise apres interruption en un banc officiel unique."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    SUCCESS_METRICS, arm_statistics, paired_comparisons, summarise, write_json_atomically,
)

ARMS = [
    "OpexAI",
    "OpexAI[air_fleet_buffer=-1]",
    "OpexAI[air_cadence_cap=0]",
    "OpexAI[c50b_road_cap_relax=1]",
    "OpexAI[road_loading_fix=1]",
]
EXTRA_METRICS = ("n_vehicles", "n_stations")


def exact_sign_pvalue(wins, losses):
    n = wins + losses
    if n == 0:
        return None
    tail = sum(math.comb(n, k) for k in range(0, min(wins, losses) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def paired_extra(summary, arms):
    indexed = {(r["arm"], r["seed"]): r for r in summary if r["run_ok"]}
    comparisons = []
    baseline = arms[0]
    for variant in arms[1:]:
        seeds = sorted(seed for arm, seed in indexed if arm == baseline and (variant, seed) in indexed)
        metrics = {}
        for metric in EXTRA_METRICS:
            deltas = [indexed[variant, seed][metric] - indexed[baseline, seed][metric] for seed in seeds]
            wins = sum(delta > 0 for delta in deltas)
            losses = sum(delta < 0 for delta in deltas)
            metrics[metric] = {
                "n": len(deltas),
                "mean_variant_minus_baseline": round(sum(deltas) / len(deltas), 6) if deltas else None,
                "wins": wins,
                "losses": losses,
                "ties": len(deltas) - wins - losses,
                "sign_test_two_sided_p": round(exact_sign_pvalue(wins, losses), 6) if wins + losses else None,
            }
        comparisons.append({"baseline": baseline, "variant": variant, "shared_seeds": seeds, "metrics": metrics})
    return comparisons


def inject_exact_sign_tests(comparisons, summary):
    indexed = {(r["arm"], r["seed"]): r for r in summary if r["run_ok"]}
    for comparison in comparisons:
        a, b = comparison["arm_a"], comparison["arm_b"]
        for metric, stats in comparison["metrics"].items():
            deltas = [
                indexed[a, seed][metric] - indexed[b, seed][metric]
                for seed in comparison["shared_seeds"]
                if indexed[a, seed].get(metric) is not None and indexed[b, seed].get(metric) is not None
            ]
            wins = sum(delta > 0 for delta in deltas)
            losses = sum(delta < 0 for delta in deltas)
            stats["arm_b_beats_arm_a"] = losses
            stats["ties"] = len(deltas) - wins - losses
            stats["sign_test_two_sided_p"] = round(exact_sign_pvalue(wins, losses), 6) if wins + losses else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--extension", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.checkpoint.read_text().splitlines() if line.strip()]
    interrupted = summarise(rows, expected_last_year=1979)
    retained = [r for r in interrupted if r["arm"] in ARMS[:2] and r["run_ok"]]
    remaining_payload = json.loads(args.remaining.read_text())
    retained.extend(remaining_payload["summary"])
    extension_payload = None
    if args.extension is not None:
        extension_payload = json.loads(args.extension.read_text())
        retained.extend(extension_payload["summary"])
    for record in retained:
        record.pop("openttd_output", None)

    by_arm_seed = {(r["arm"], r["seed"]): r for r in retained}
    initial_seeds = list(remaining_payload["seeds"])
    extension_seeds = list(extension_payload["seeds"]) if extension_payload else []
    seeds_by_arm = {
        arm: initial_seeds + ([] if arm == "OpexAI[air_fleet_buffer=-1]" else extension_seeds)
        for arm in ARMS
    }
    missing = [
        (arm, seed) for arm, seeds in seeds_by_arm.items() for seed in seeds
        if (arm, seed) not in by_arm_seed
    ]
    failed = [r for r in retained if not r["run_ok"]]
    if missing or failed:
        raise SystemExit(f"campagne incomplete: missing={missing}, failed={failed}")

    paired = paired_comparisons(retained, ARMS)
    inject_exact_sign_tests(paired, retained)
    payload = {
        "openttd_version": remaining_payload["openttd_version"],
        "opengfx_version": remaining_payload["opengfx_version"],
        "years": 10,
        "starting_year": 1970,
        "seeds": initial_seeds + extension_seeds,
        "seeds_by_arm": seeds_by_arm,
        "arms": ARMS,
        "design": (
            "official paired 20 seeds x 10 years; extended to 40 paired seeds for the three "
            "initially inconclusive variants; resumed from an interrupted campaign"
        ),
        "sources": {
            "checkpoint": str(args.checkpoint),
            "remaining": str(args.remaining),
            "extension": str(args.extension) if args.extension else None,
        },
        "success_metrics": list(SUCCESS_METRICS),
        "summary": retained,
        "failed_runs": [],
        "failed_run_count": 0,
        "statistics": arm_statistics(retained, ARMS),
        "paired_comparisons": paired,
        "paired_physical_counts": paired_extra(retained, ARMS),
    }
    write_json_atomically(args.out, payload)
    print("ecrit", args.out)
    for comparison in paired:
        if comparison["arm_a"] != ARMS[0]:
            continue
        print("\n", comparison["arm_b"])
        for metric in ("company_value", "profit_year", "performance_history", "median_station_rating"):
            stats = comparison["metrics"][metric]
            print(metric, stats["mean_difference"], stats["arm_a_beats_arm_b"],
                  stats["arm_b_beats_arm_a"], stats["ties"], stats["sign_test_two_sided_p"])


if __name__ == "__main__":
    main()
