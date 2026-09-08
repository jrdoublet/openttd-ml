"""Banc apparie C36.3 : air_cheap_site=1 contre le defaut, 10 graines x 1 an.

keep() rend un tuple. Lecture PLYR.old_economy. script=4 pour AIR_PLAN_PERF.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    CHECKPOINT_PATH,
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

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

SEEDS = (42, 100, 7, 999, 2026, 1, 17, 73, 314, 512)
ARMS = ("OpexAI", "OpexAI[air_cheap_site=1]")
YEARS = 1
PERF_RE = re.compile(
    r"AIR_PLAN_PERF: total_ops=(\d+) ops_sites=(\d+) ops_eval=(\d+) "
    r"ticks=(\d+) days=(\d+) probes=(\d+) cheap_skip=(\d+) sites=(\d+)"
)


def first_air_plan_perf(output):
    for line in (output or "").splitlines():
        m = PERF_RE.search(line)
        if m:
            return {
                "total_ops": int(m.group(1)),
                "ops_sites": int(m.group(2)),
                "ops_eval": int(m.group(3)),
                "ticks": int(m.group(4)),
                "days": int(m.group(5)),
                "probes": int(m.group(6)),
                "cheap_skip": int(m.group(7)),
                "sites": int(m.group(8)),
            }
    return None


def attach_first_scans(summary):
    for record in summary:
        record["first_scan"] = first_air_plan_perf(record.get("openttd_output"))
        record["openttd_output"] = ""
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
    )
    parser.add_argument("--max-workers", type=int, default=5)
    args = parser.parse_args()
    seeds = tuple(args.seeds) if args.seeds else SEEDS
    if args.out is None:
        tag = "10seeds" if args.seeds is None else "s" + "-".join(str(s) for s in seeds)
        args.out = ROOT / "results" / f"bench_c36_3_cheap_site_{args.years}y_{tag}.json"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
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
        experiments=experiments(built, list(seeds), args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = attach_first_scans(summarise(rows))
    failed = [r for r in summary if not r["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "starting_year": 1970,
        "seeds": list(seeds),
        "arms": list(ARMS),
        "repeats": 1,
        "openttd_config": cfg,
        "metric": (
            "PLYR[0].old_economy[0] : company_value, performance_history, "
            "profit, profit_year ; STNN median_station_rating ; "
            "first AIR_PLAN_PERF probes/sites"
        ),
        "success_metrics": list(SUCCESS_METRICS),
        "paired_reading": "mean(A(seed) - B(seed))",
        "checkpoint": str(bench_v2.CHECKPOINT_PATH),
        "summary": summary,
        "failed_runs": [
            {"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]}
            for r in failed
        ],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(args.out, payload)
    print(json.dumps({
        "out": str(args.out),
        "failed": len(failed),
        "paired": payload["paired_comparisons"],
        "first_scans": [
            {
                "arm": r["arm"],
                "seed": r["seed"],
                "company_value": r["company_value"],
                "profit_year": r["profit_year"],
                "n_vehicles": r["n_vehicles"],
                "n_stations": r["n_stations"],
                "first_scan": r["first_scan"],
            }
            for r in summary
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
