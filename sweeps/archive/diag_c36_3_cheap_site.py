"""Sonde C36.3 air_cheap_site : premier scan AIR_PLAN_PERF, graine 42, 1 an.

Compare OpexAI (historique) a OpexAI[air_cheap_site=1]. Sans decision_log : AIR_PLAN_PERF
est un AILog.Info inconditionnel, capture via -d script=4. keep() rend un tuple.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

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


def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    perf = first_air_plan_perf(row.get("output", ""))
    experiment = row["experiment"]
    arm = experiment.get("bench_arm")
    if not arm:
        run = experiment.get("bench_run") or []
        arm = run[0] if run else "unknown"
    return ({
        "arm": arm,
        "seed": experiment["seed"],
        "company_value": last_closed.get("company_value", 0),
        "profit_year": year_profit(closed) or 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "first_scan": perf,
    },)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "results" / "diag_c36_3_cheap_site_y1.json"))
    args = parser.parse_args()
    enable_savegame_cleanup()
    arms = {
        "OpexAI": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI"),
        "OpexAI[air_cheap_site=1]": local_folder(
            str(ROOT / "ai" / "OpexAI"), "OpexAI", (("air_cheap_site", 1),)
        ),
    }
    cfg = make_cfg(1970)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=2,
        result_processor=keep,
        experiments=[
            {
                "seed": 42,
                "days": 365,
                "openttd_config": cfg,
                "ais": (arms[name],),
                "bench_arm": name,
                "bench_run": [name, 42, 0],
            }
            for name in arms
        ],
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    last = {}
    first_scan = {}
    for rec in rows:
        last[rec["arm"]] = rec
        if rec.get("first_scan") and rec["arm"] not in first_scan:
            first_scan[rec["arm"]] = rec["first_scan"]
    for arm, rec in last.items():
        rec["first_scan"] = first_scan.get(arm)
    payload = {"summary": list(last.values())}
    Path(args.out).write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
