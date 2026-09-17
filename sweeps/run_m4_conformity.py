"""M4 : bancs de conformité ciblés max_trains=0 et pf.forbid_90_deg=1."""
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
from bench_v2 import enable_savegame_cleanup, summarise, write_json_atomically
from diag_m4_conformity import analyse_logs, scenario_summary

DEFAULT_SEEDS = [42, 100, 999, 1234, 5678]
SETTINGS = (
    ("decision_log", 1),
    ("c63_invest_probe", 1),
    ("air_early_slot", 1),
    ("abandon_gen_filter", 1),
    ("abandon_cooldown_days", 365),
)

_real_check_output = openttdlab.subprocess.check_output
def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)
openttdlab.subprocess.check_output = _check_output_with_script_debug


def cfg_for(scenario, year=1970, map_size=8):
    cfg = bench_v2.make_cfg(year, map_size)
    if scenario == "control":
        pass
    elif scenario == "max_trains_0":
        cfg += "\n[vehicle]\nmax_trains = 0\n"
    elif scenario == "forbid_90":
        cfg += "\n[pf]\nforbid_90_deg = true\n"
    else:
        raise ValueError(scenario)
    return cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--scenarios", nargs="+", default=["max_trains_0", "forbid_90"])
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "review_m4_conformity_5x6.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    engine_root = args.out.with_name(args.out.stem + "_engine")
    engine_root.mkdir(parents=True, exist_ok=True)
    enable_savegame_cleanup()
    duel.enable_engine_failure_capture()
    all_summary = []
    scenario_results = {}
    libraries = tuple(bananas_ai_library(spec["unique_id"], spec["name"]) for spec in duel.LIBRARY_SPECS)
    for scenario in args.scenarios:
        policy_id = f"m4_{scenario}"
        policies = ({"id": policy_id, "role": "diagnostic", "explicit_settings": SETTINGS},)
        exps = duel.make_experiments_plan(
            args.seeds, args.years, repeats=1, campaign=None,
            policy_id=policy_id, policies=policies,
        )
        scenario_dir = engine_root / scenario
        scenario_dir.mkdir(parents=True, exist_ok=True)
        for experiment in exps:
            experiment["openttd_config"] = cfg_for(scenario)
            experiment["scenario"] = scenario
            experiment["engine_log_path"] = str(duel.engine_log_path_for(
                scenario_dir, experiment["seed"], experiment.get("repeat", 0), policy_id=policy_id
            ))
        rows = list(run_experiments(
            openttd_version=duel.OPENTTD_VERSION,
            opengfx_version=duel.OPENGFX_VERSION,
            max_workers=args.workers,
            result_processor=duel.keep,
            experiments=exps,
            ai_libraries=libraries,
        ))
        expected_last_year = duel.STARTING_YEAR + args.years - 1
        summary = summarise(rows, expected_last_year=expected_last_year, expected_savegames=args.years * 12)
        for row in summary:
            row["scenario"] = scenario
        all_summary.extend(summary)
        scenario_results[scenario] = {
            "health": {
                "expected_runs": len(args.seeds) * 2,
                "observed_runs": len(summary),
                "failed_runs": [
                    {"arm": row["arm"], "seed": row["seed"], "reason": row.get("failure_reason")}
                    for row in summary if not row.get("run_ok")
                ],
            },
            "opex": scenario_summary(summary, scenario),
            "logs": analyse_logs(scenario_dir),
        }
    payload = {
        "purpose": "M4 conformity measurement-only; no policy/default adoption.",
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "settings": dict(SETTINGS),
        "scenarios": scenario_results,
        "summary": all_summary,
    }
    write_json_atomically(args.out, payload)
    for scenario, data in scenario_results.items():
        logs = data["logs"]
        print(
            f"{scenario}: runs={data['health']['observed_runs']}/{data['health']['expected_runs']} "
            f"failed={len(data['health']['failed_runs'])} rail_fail={logs['rail_build_fail_reasons']} "
            f"rail_actual_fail={logs['rail_spend']['actual_fail']} noai_errors={logs['noai_errors']}"
        )
    print(f"Sortie: {args.out}")
    if any(data["health"]["failed_runs"] for data in scenario_results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
