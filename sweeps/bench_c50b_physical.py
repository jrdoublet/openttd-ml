"""Banc apparie C50b avec repartition physique des flottes et raisons d'upgrade rail.

Le banc macro canonique ne conserve que le nombre brut d'entrees VEHS. Ce harnais garde en plus
les vehicules primaires de la compagnie par mode et les panneaux RU emis par le chemin normal de
doublement du rail. Il n'active aucune sonde Squirrel et ne modifie donc pas les decisions de l'IA.
"""
import argparse
from collections import Counter
import json
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
from physical_counters import decode_vehicles

TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}


def physical_telemetry(chunks, owner=0):
    dec = decode_vehicles(chunks.get("VEHS"), target_owner=owner)
    if not dec["chunk_valid"]:
        return {
            "schema_version": dec["schema_version"],
            "qualified_modes": dec["qualified_modes"],
            "chunk_valid": False,
            "chunk_error": dec["chunk_error"],
            "primary_vehicles_by_mode": None,
            "primary_vehicles_count": None,
            "vehicle_pool_entries": None,
            "components_breakdown": None,
            "rail_upgrade_reasons": {},
            "rail_upgrade_signs": [],
        }

    by_mode = dec["primary_vehicles_by_mode"]
    counts = {
        "train": by_mode.get("rail", 0),
        "roadveh": by_mode.get("road", 0),
        "ship": by_mode.get("water", 0),
        "aircraft": by_mode.get("air", 0),
    }

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
        "schema_version": dec["schema_version"],
        "qualified_modes": dec["qualified_modes"],
        "chunk_valid": True,
        "primary_vehicles_by_mode": counts,
        "primary_vehicles_count": dec["primary_vehicles_count"],
        "vehicle_pool_entries": dec["vehicle_pool_entries"],
        "components_breakdown": dec["components_breakdown"],
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
    indexed = {
        (r["arm"], r["seed"]): r for r in summary
        if r.get("run_ok") and r.get("primary_vehicles_by_mode") is not None
    }
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
                    if indexed[arm_a, seed]["primary_vehicles_by_mode"].get(mode) is not None
                    and indexed[arm_b, seed]["primary_vehicles_by_mode"].get(mode) is not None
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
    parser.add_argument("--arms", nargs="+", default=[])
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--out", type=Path, default=Path("results/bench_c50b_physical.json"))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--selftest", action="store_true", help="Vérifie la télémétrie physique et le fail-closed")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.arms:
        parser.error("--arms est obligatoire hors --selftest")
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
        chunk_valid = raw.get("chunk_valid", True)
        record.update({
            "schema_version": raw.get("schema_version"),
            "qualified_modes": raw.get("qualified_modes"),
            "chunk_valid": chunk_valid,
            "chunk_error": raw.get("chunk_error"),
            "primary_vehicles_by_mode": raw.get("primary_vehicles_by_mode"),
            "primary_vehicles_count": raw.get("primary_vehicles_count"),
            "vehicle_pool_entries": raw.get("vehicle_pool_entries"),
            "components_breakdown": raw.get("components_breakdown"),
            "rail_upgrade_reasons": raw.get("rail_upgrade_reasons", {}),
            "rail_upgrade_signs": raw.get("rail_upgrade_signs", []),
        })
        if chunk_valid is False:
            record["run_ok"] = False
            if not record.get("failure_reason"):
                record["failure_reason"] = f"physical_decode_failure: {raw.get('chunk_error')}"
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
        modes = record.get("primary_vehicles_by_mode")
        if modes is not None:
            modes_str = f"rail={modes.get('train', 0)} road={modes.get('roadveh', 0)} air={modes.get('aircraft', 0)}"
        else:
            modes_str = f"MODES=FAIL ({record.get('chunk_error')})"
        print(
            f"{record['arm']:>64} seed={record['seed']:<8} "
            f"value={record['company_value']} profit={record['profit_year']} "
            f"{modes_str} "
            f"RU={record.get('rail_upgrade_reasons')}"
        )
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} run(s)")


def selftest():
    """Vérifie la télémétrie physique et la robustesse fail-closed face aux chunks manquants."""
    fixture_path = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            c66 = json.load(f)
        tel = physical_telemetry(c66["chunks"], owner=0)
        assert tel["chunk_valid"] is True, "Télémétrie valide attendue sur fixture C66"
        assert tel["schema_version"] in ("1.1.0", "1.2.0")
        assert tel["primary_vehicles_by_mode"]["train"] == 1
        assert tel["primary_vehicles_by_mode"]["roadveh"] == 17
        assert tel["primary_vehicles_by_mode"]["aircraft"] == 3

    # Test chunk absent
    tel_bad = physical_telemetry({"VEHS": None}, owner=0)
    assert tel_bad["chunk_valid"] is False
    assert tel_bad["chunk_error"] == "chunk_missing"
    assert tel_bad["primary_vehicles_by_mode"] is None

    # Test summary et physical_comparisons avec run invalide
    mock_summary = [
        {
            "arm": "ArmA", "seed": 42, "repeat": 0, "run_ok": True,
            "company_value": 100000, "profit_year": 10000,
            "primary_vehicles_by_mode": {"train": 1, "roadveh": 5, "ship": 0, "aircraft": 2},
        },
        {
            "arm": "ArmA", "seed": 100, "repeat": 0, "run_ok": False,
            "failure_reason": "physical_decode_failure: chunk_missing",
            "company_value": 0, "profit_year": 0,
            "primary_vehicles_by_mode": None,  # Ne doit pas faire crasher physical_comparisons
        },
        {
            "arm": "ArmB", "seed": 42, "repeat": 0, "run_ok": True,
            "company_value": 90000, "profit_year": 9000,
            "primary_vehicles_by_mode": {"train": 0, "roadveh": 6, "ship": 0, "aircraft": 1},
        },
    ]
    comps = physical_comparisons(mock_summary, ["ArmA", "ArmB"])
    assert len(comps) == 1
    assert comps[0]["shared_seeds"] == [42]
    assert comps[0]["modes"]["train"]["mean_difference"] == 1.0
    print("Selftest bench_c50b_physical.py réussi avec succès !")


if __name__ == "__main__":
    main()
