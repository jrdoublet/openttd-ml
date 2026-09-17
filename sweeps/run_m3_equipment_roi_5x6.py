"""M3/G12 : diagnostic passif équipement, OpexAI vs AAAHogEx sur carte partagée."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_1v1_5y_20seeds as duel
import bench_v2
from bench_v2 import arm_statistics, enable_savegame_cleanup, paired_comparisons, summarise, write_json_atomically
from diag_m3_equipment_roi import analyse

DEFAULT_SEEDS = [42, 100, 999, 1234, 5678]
POLICY_ID = "m3_equipment_roi_probe"
SETTINGS = (("probe_events", 1), ("air_early_slot", 1), ("abandon_gen_filter", 1), ("abandon_cooldown_days", 365))

_real_check_output = openttdlab.subprocess.check_output
def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)
openttdlab.subprocess.check_output = _check_output_with_script_debug

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "review_m3_equipment_roi_5x6.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = args.out.with_suffix(".jsonl")
    engine_dir = args.out.with_name(args.out.stem + "_engine")
    engine_dir.mkdir(parents=True, exist_ok=True)
    if checkpoint.exists():
        checkpoint.unlink()
    duel.CHECKPOINT_PATH = checkpoint
    duel.ENGINE_LOG_DIR = engine_dir
    duel.LINE_TELEMETRY = True
    bench_v2.CHECKPOINT_PATH = checkpoint
    duel.enable_engine_failure_capture()
    enable_savegame_cleanup()
    policies = ({"id": POLICY_ID, "role": "diagnostic", "explicit_settings": SETTINGS},)
    experiments = duel.make_experiments_plan(args.seeds, args.years, repeats=1, campaign=None, policy_id=POLICY_ID, policies=policies)
    for experiment in experiments:
        experiment["engine_log_path"] = str(duel.engine_log_path_for(engine_dir, experiment["seed"], experiment.get("repeat", 0), policy_id=POLICY_ID))
    libraries = tuple(bananas_ai_library(spec["unique_id"], spec["name"]) for spec in duel.LIBRARY_SPECS)
    rows = list(run_experiments(
        openttd_version=duel.OPENTTD_VERSION,
        opengfx_version=duel.OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=duel.keep,
        experiments=experiments,
        ai_libraries=libraries,
    ))
    expected_last_year = duel.STARTING_YEAR + args.years - 1
    summary = summarise(rows, expected_last_year=expected_last_year, expected_savegames=args.years * 12)
    failed = [row for row in summary if not row["run_ok"]]
    metrics = ("company_value", "profit_year", "performance_history", "primary_vehicles", "n_stations")
    payload = {
        "campaign_id": args.out.stem,
        "policy_id": POLICY_ID,
        "purpose": "M3/G12 descriptive measurement-only; no equipment policy/default adoption from this 5x6.",
        "openttd_version": duel.OPENTTD_VERSION,
        "opengfx_version": duel.OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "settings": dict(SETTINGS),
        "expected_last_year": expected_last_year,
        "summary": summary,
        "failed_runs": [{"arm": row["arm"], "seed": row["seed"], "reason": row["failure_reason"]} for row in failed],
        "health": {
            "expected_runs": len(args.seeds) * 2,
            "observed_runs": len(summary),
            "all_runs_present": len(summary) == len(args.seeds) * 2,
            "all_runs_healthy_complete_horizon": not failed,
        },
        "statistics": arm_statistics(summary, list(duel.ARMS), metrics),
        "paired_comparisons": paired_comparisons(summary, list(duel.ARMS), metrics),
        "line_telemetry": duel.build_line_telemetry_report(rows),
    }
    payload["m3_analysis"] = analyse(payload, engine_dir)
    write_json_atomically(args.out, payload)
    analysis = payload["m3_analysis"]
    print(f"M3 diagnostic: runs={len(summary)}/{len(args.seeds) * 2} failed={len(failed)} events={analysis['event_count']}")
    for mode, stats in analysis["by_mode"].items():
        print(f"{mode}: compare={stats['comparison_events']} multi={stats['multi_choice_events']} diff_profit={stats['selected_differs_best_profit']} diff_roi={stats['selected_differs_best_roi']} admission_flips={stats['admission_flips']} cap_delta_nonzero={stats['capacity_delta_nonzero']}")
    print(f"Sortie: {args.out}")
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
