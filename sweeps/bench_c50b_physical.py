"""Banc apparie C50b avec repartition physique des flottes et raisons d'upgrade rail.

Le banc macro canonique ne conserve que le nombre brut d'entrees VEHS. Ce harnais garde en plus
les vehicules primaires de la compagnie par mode et les panneaux RU emis par le chemin normal de
doublement du rail. Il n'active aucune sonde Squirrel et ne modifie donc pas les decisions de l'IA.
"""
import argparse
from collections import Counter
from pathlib import Path
import sys

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, SEEDS, SUCCESS_METRICS,
    arm_statistics, build_arms, enable_savegame_cleanup, experiments,
    make_cfg, paired_comparisons, summarise, write_json_atomically,
)

TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def physical_telemetry(chunks, owner=0):
    counts = {mode: 0 for mode in TYPE_TO_MODE.values()}
    vehs = chunks.get("VEHS") or {}
    vehs_list = vehs.values() if isinstance(vehs, dict) else vehs
    for vehicle in vehs_list:
        if not isinstance(vehicle, dict):
            continue
        mode = TYPE_TO_MODE.get(str(vehicle.get("type")))
        if mode is None:
            continue
        body = _first(vehicle.get(mode))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue
        counts[mode] += 1

    reasons = Counter()
    rail_upgrade_signs = []
    signs = chunks.get("SIGN") or {}
    signs_list = signs.values() if isinstance(signs, dict) else signs
    for sign in signs_list:
        name = sign.get("name", "") if isinstance(sign, dict) else ""
        if not name.startswith("RU|"):
            continue
        rail_upgrade_signs.append(name)
        parts = name.split("|", 3)
        reasons[parts[3] if len(parts) == 4 else "MALFORMED"] += 1
    return {
        "primary_vehicles_by_mode": counts,
        "rail_upgrade_reasons": dict(reasons),
        "rail_upgrade_signs": rail_upgrade_signs,
    }


def keep_with_physical_telemetry(row):
    base = bench_v2.keep(row)[0]
    base.update(physical_telemetry(row.get("chunks", {})))
    return (base,)


def final_telemetry(rows):
    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        if key not in by_run or row["date"] > by_run[key]["date"]:
            by_run[key] = row
    return by_run


def physical_comparisons(summary, arms):
    fields = tuple(TYPE_TO_MODE.values())
    indexed = {(r["arm"], r["seed"]): r for r in summary if r["run_ok"]}
    comparisons = []
    for index, arm_a in enumerate(arms):
        for arm_b in arms[index + 1:]:
            shared = sorted(seed for a, seed in indexed if a == arm_a and (arm_b, seed) in indexed)
            modes = {}
            for mode in fields:
                deltas = [
                    indexed[arm_a, seed]["primary_vehicles_by_mode"][mode]
                    - indexed[arm_b, seed]["primary_vehicles_by_mode"][mode]
                    for seed in shared
                ]
                modes[mode] = {
                    "n": len(deltas),
                    "mean_difference": round(sum(deltas) / len(deltas), 6) if deltas else None,
                    "arm_a_beats_arm_b": sum(delta > 0 for delta in deltas),
                }
            comparisons.append({"arm_a": arm_a, "arm_b": arm_b, "shared_seeds": shared, "modes": modes})
    return comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    if args.years <= 0 or args.max_workers not in (1, 2, 3) or not args.seeds:
        parser.error("--years/--seeds invalides ; --max-workers doit valoir 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    try:
        built = build_arms(args.arms)
    except ValueError as error:
        parser.error(str(error))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    cfg = make_cfg(args.starting_year)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep_with_physical_telemetry,
        experiments=experiments(built, args.seeds, args.years, 1, args.starting_year, 8),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows, expected_last_year=args.starting_year + args.years - 1)
    telemetry = final_telemetry(rows)
    for record in summary:
        raw = telemetry.get((record["arm"], record["seed"], record["repeat"])) or {}
        record.update({
            "primary_vehicles_by_mode": raw.get("primary_vehicles_by_mode", {m: 0 for m in TYPE_TO_MODE.values()}),
            "rail_upgrade_reasons": raw.get("rail_upgrade_reasons", {}),
            "rail_upgrade_signs": raw.get("rail_upgrade_signs", []),
        })
        record.pop("openttd_output", None)
    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "starting_year": args.starting_year,
        "seeds": args.seeds,
        "arms": args.arms,
        "openttd_config": cfg,
        "design": "paired; no Squirrel probe; physical telemetry read from savegame chunks",
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": failed,
        "failed_run_count": len(failed),
        "statistics": arm_statistics(summary, args.arms),
        "paired_comparisons": paired_comparisons(summary, args.arms),
        "physical_comparisons": physical_comparisons(summary, args.arms),
    }
    write_json_atomically(args.out, payload)
    print("ecrit", args.out)
    print("failed runs:", len(failed))
    for record in summary:
        modes = record["primary_vehicles_by_mode"]
        print(
            f"{record['arm']:>64} seed={record['seed']:<8} "
            f"value={record['company_value']} profit={record['profit_year']} "
            f"rail={modes['train']} road={modes['roadveh']} air={modes['aircraft']} "
            f"RU={record['rail_upgrade_reasons']}"
        )
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} run(s)")


if __name__ == "__main__":
    main()
