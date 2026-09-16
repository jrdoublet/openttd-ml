"""Diagnostic AIR fleet depth sur la politique early_slot adoptee.

Reutilise la sonde C50 passive existante pour compter les motifs de refus de
_resizeAirFleets sans changer le comportement de l'IA.
"""

import argparse
import json
from pathlib import Path
import statistics
import sys

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import bench_v2
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    summarise,
    write_json_atomically,
)
from diag_c50_chronology_probe import (
    aggregate_across_seeds,
    parse_events,
    process_c50_events,
)


ARM = "OpexAI[air_early_slot=1,c50_chronology_probe=1]"
DEFAULT_SEEDS = [42, 100, 999, 1234, 5678]


def extract_line_profit_events(events):
    rows = []
    for event in events:
        if event.get("phase") != "line_profit":
            continue
        try:
            row = {
                "year": int(event.get("year", event.get("_log_year", 0))),
                "profit_year": int(event.get("profit_year", 0)),
                "line": int(event.get("line", -1)),
                "mode": event.get("mode", "unknown"),
                "cargo": event.get("cargo", "unknown"),
                "vehicles": int(event.get("vehs", 0)),
                "profit": int(event.get("profit", 0)),
                "pred_profit": int(event.get("pred_profit", 0)),
                "age": int(event.get("age", -1)),
            }
        except (TypeError, ValueError):
            continue
        rows.append(row)
    return rows


def summarise_air_prediction(rows):
    air = [row for row in rows if row["mode"] == "air" and row["pred_profit"] > 0]
    ratios = [row["profit"] / row["pred_profit"] for row in air]
    return {
        "n": len(air),
        "pred_profit_mean": round(statistics.mean(row["pred_profit"] for row in air), 2) if air else None,
        "profit_mean": round(statistics.mean(row["profit"] for row in air), 2) if air else None,
        "real_over_pred_mean": round(statistics.mean(ratios), 6) if ratios else None,
        "real_over_pred_median": round(statistics.median(ratios), 6) if ratios else None,
        "real_below_half_pred": sum(row["profit"] < 0.5 * row["pred_profit"] for row in air),
        "real_below_quarter_pred": sum(row["profit"] < 0.25 * row["pred_profit"] for row in air),
        "real_nonpositive": sum(row["profit"] <= 0 for row in air),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", default=ARM)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/diag_air_fleet_depth_early_slot_5x6_v1.json"),
    )
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()

    enable_savegame_cleanup()
    arms = build_arms([args.arm])
    exps = experiments(arms, args.seeds, args.years, repeats=1, starting_year=1970)

    rows = list(
        run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            max_workers=min(args.workers, len(args.seeds)),
            result_processor=keep,
            experiments=exps,
            ai_libraries=(
                bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
        )
    )

    expected_last_year = 1970 + args.years - 1
    summary = summarise(rows, expected_last_year=expected_last_year)
    if len(summary) != len(args.seeds):
        raise SystemExit(
            f"ABORT: attendu {len(args.seeds)} graines, obtenu {len(summary)} dans summary"
        )

    failed = [
        {key: value for key, value in record.items() if key != "openttd_output"}
        for record in summary
        if not record["run_ok"]
    ]
    if failed:
        raise SystemExit(f"ABORT: {len(failed)} runs ont echoue: {failed}")

    results_by_seed = {}
    line_profit_events_by_seed = {}
    for record in summary:
        events = parse_events(record.get("openttd_output", ""))
        results_by_seed[record["seed"]] = process_c50_events(events)
        line_profit_events_by_seed[record["seed"]] = extract_line_profit_events(events)

    cumulative = aggregate_across_seeds(results_by_seed)
    all_line_profit_events = [
        row for seed_rows in line_profit_events_by_seed.values() for row in seed_rows
    ]
    air_prediction_by_age = {}
    ages = sorted({
        row["age"] for row in all_line_profit_events
        if row["mode"] == "air" and row["age"] >= 0
    })
    for age in ages:
        air_prediction_by_age[str(age)] = summarise_air_prediction([
            row for row in all_line_profit_events if row["age"] == age
        ])
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": min(args.workers, len(args.seeds)),
        "arm": args.arm,
        "by_seed": results_by_seed,
        "cumulative": cumulative,
        "line_profit_events_by_seed": line_profit_events_by_seed,
        "air_prediction": {
            "all": summarise_air_prediction(all_line_profit_events),
            "by_age": air_prediction_by_age,
        },
        "failed_runs": failed,
        "failed_run_count": len(failed),
    }
    write_json_atomically(args.out, payload)

    print("year lines planes cap lines_at_cap W M C Y L S X fleet_added_air")
    for year in sorted(
        {int(y) for seed_data in results_by_seed.values() for y in seed_data}
    ):
        air_rows = []
        added = 0
        for seed_data in results_by_seed.values():
            row = seed_data.get(year) or seed_data.get(str(year))
            if not row:
                continue
            air = (row.get("non_expansion") or {}).get("air")
            if air:
                air_rows.append(air)
            added += (
                (row.get("fleet_built") or {})
                .get("by_mode", {})
                .get("air", {})
                .get("added", 0)
            )
        def total(key):
            return sum(r.get(key, 0) for r in air_rows)
        print(
            year,
            total("lines"),
            total("planes_total"),
            total("cap_physical"),
            total("lines_at_cap"),
            total("ref_W"),
            total("ref_M"),
            total("ref_C"),
            total("ref_Y"),
            total("ref_L"),
            total("ref_S"),
            total("ref_X"),
            added,
        )

    print(f"Resultats enregistres dans {args.out}")
    print("AIR prediction all:", payload["air_prediction"]["all"])
    for age, stats in payload["air_prediction"]["by_age"].items():
        print("AIR prediction age", age, stats)


if __name__ == "__main__":
    main()
