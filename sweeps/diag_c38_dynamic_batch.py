"""Diagnostic C38 : 5 graines x 6 ans, journal du batch dynamique."""
import argparse
from collections import Counter
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2
from bench_v2 import (OPENTTD_VERSION, OPENGFX_VERSION, build_arms,
                      enable_savegame_cleanup, experiments, keep, make_cfg,
                      summarise, write_json_atomically)

SEEDS = (42, 100, 7, 999, 2026)
ARM = "OpexAI[portfolio_dynamic_batch=1,decision_log=1]"
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ DYNAMIC_BATCH\s+(.*)$")
_real_check_output = openttdlab.subprocess.check_output


def _with_script_log(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _with_script_log


def fields(text):
    result = {}
    for token in text.split():
        if "=" in token:
            key, value = token.split("=", 1)
            result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_c38_dynamic_batch_6y_5seeds.json")
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([ARM]), list(SEEDS), 6, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    summary = summarise(rows)
    reports = []
    for row in summary:
        events = []
        for line in (row.get("openttd_output") or "").splitlines():
            match = EVENT_RE.search(line)
            if match:
                events.append(fields(match.group(1)))
        stops = Counter(e.get("reason", "unknown") for e in events if e.get("action") == "stop")
        continues = [e for e in events if e.get("action") == "continue"]
        reports.append({
            "seed": row["seed"], "run_ok": row["run_ok"],
            "company_value": row["company_value"], "profit_year": row["profit_year"],
            "n_stations": row["n_stations"], "n_vehicles": row["n_vehicles"],
            "continue_events": len(continues),
            "multi_build_events": sum(int(e.get("built", 0)) > 1 for e in continues),
            "max_built": max([int(e.get("built", 0)) for e in events] or [0]),
            "max_attempted": max([int(e.get("attempted", 0)) for e in events] or [0]),
            "stop_reasons": dict(stops),
        })
    payload = {"arm": ARM, "years": 6, "seeds": list(SEEDS), "reports": reports}
    write_json_atomically(args.out, payload)
    for report in reports:
        print(report)
    if any(not report["run_ok"] for report in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
