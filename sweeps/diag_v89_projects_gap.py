"""Diagnostic solo : V89 espace-t-il les passages de `projects` pendant une recherche A* rail ?

Reprend le harnais de diag_v88_investigation.py (bench_v2, -d script=4) et ne garde que :
- C56_TASK TASK_ENTER name=projects (sous probe_events) ;
- C56_TASK RAIL_SEARCH_START / RAIL_SEARCH_END ;
- C50_CHRONO phase=project_built (sous la sonde C50 si active) et C78_SLOT projects_pass/pass_stop.
Aucune decision n'est modifiee ; les sondes perturbent la trajectoire de facon identique aux deux bras
seulement en premiere approximation : comparer aussi les parties sans sonde.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab
from openttdlab import bananas_ai_library, run_experiments
import bench_v2
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_LINE_RE = re.compile(r"OPEX ((\d{4})-(\d{1,2})-(\d{1,2})) ([A-Z0-9_]+)\s*(.*)")
KEEP_C56 = ("RAIL_SEARCH_START", "RAIL_SEARCH_END")


def fields_of(rest):
    out = {}
    for token in rest.split():
        if "=" in token:
            k, v = token.split("=", 1)
            out[k] = v
    return out


def extract(output):
    events = []
    for line in (output or "").splitlines():
        m = OPEX_LINE_RE.search(line)
        if not m:
            continue
        date, _, _, _, tag, rest = m.groups()
        if tag == "C56_TASK":
            parts = rest.split(None, 1)
            kind = parts[0] if parts else ""
            f = fields_of(parts[1] if len(parts) > 1 else "")
            if kind == "TASK_ENTER" and f.get("name") == "projects":
                events.append({"date": date, "type": "projects_enter", "tick": f.get("tick")})
            elif kind in KEEP_C56:
                events.append({"date": date, "type": kind.lower(), **f})
        elif tag == "C78_SLOT":
            f = fields_of(rest)
            if f.get("phase") in ("projects_pass", "pass_stop"):
                events.append({"date": date, "type": "c78_" + f["phase"], **f})
        elif tag == "C50_CHRONO":
            f = fields_of(rest)
            if f.get("phase") == "project_built":
                events.append({"date": date, "type": "project_built", **f})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[5678, 999, 100])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    bench_v2.CHECKPOINT_PATH = Path("/dev/null")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms(args.arms), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows, expected_last_year=1970 + args.years - 1, expected_savegames=args.years * 12)
    results = []
    for rec in summary:
        results.append({
            "arm": rec["arm"], "seed": rec["seed"], "run_ok": rec["run_ok"],
            "company_value": rec.get("company_value"), "profit_year": rec.get("profit_year"),
            "primary_vehicles_by_mode": rec.get("primary_vehicles_by_mode"),
            "events": extract(rec.get("openttd_output", "")),
        })
    write_json_atomically(Path(args.out), {"arms": args.arms, "seeds": args.seeds,
                                           "years": args.years, "results": results})
    print(f"Done: {args.out}")


if __name__ == "__main__":
    main()
