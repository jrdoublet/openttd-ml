"""Decision-log replay of C36.3 collapse seeds 73 and 2026, 1 year, paired."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENTTD_VERSION,
    OPENGFX_VERSION,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    make_cfg,
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

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
SEEDS = (73, 2026)
ARMS = (
    "OpexAI[decision_log=1]",
    "OpexAI[air_cheap_site=1,decision_log=1]",
)
KINDS = (
    "AIR_BUILD", "AIR_REFUSE", "AIR_PLAN_SETS", "AIR_PLAN_PERF", "AIR_PLAN_INPUT",
    "PORTFOLIO_RANK", "PROJECT_CHOSEN", "PROJECT_DISCARD", "VIVIER", "VIVIER_MIX",
    "TASK", "AFAIL", "BFAIL", "REPORT",
)


def parse_events(output):
    events = []
    for line in (output or "").splitlines():
        m = OPEX_RE.search(line)
        if not m:
            continue
        y, mo, d, kind, rest = m.groups()
        fields = {}
        for tok in rest.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                fields[k] = v
        events.append({
            "date": f"{y}-{int(mo):02d}-{int(d):02d}",
            "kind": kind,
            "fields": fields,
            "raw": m.group(0)[:240],
        })
    return events


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out if args.out is not None else (
        ROOT / "results" / "diag_c36_3_seeds_73_2026.json"
        if args.seeds == list(SEEDS) and args.years == 1
        else ROOT / "results" / f"diag_c36_3_s{'-'.join(map(str, args.seeds))}_{args.years}y.json"
    )
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(list(ARMS))
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=4,
        result_processor=keep,
        experiments=experiments(built, list(args.seeds), args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    reports = []
    for rec in summary:
        events = parse_events(rec.get("openttd_output"))
        rec["openttd_output"] = ""
        interesting = [e for e in events if e["kind"] in KINDS]
        builds = [e for e in events if e["kind"] in ("AIR_BUILD", "PROJECT_CHOSEN")]
        ranks0 = [e for e in events if e["kind"] == "PORTFOLIO_RANK" and e["fields"].get("rank") == "0"]
        refuses = [e for e in events if e["kind"] in ("AIR_REFUSE", "PROJECT_DISCARD")]
        reports.append({
            "arm": rec["arm"],
            "seed": rec["seed"],
            "company_value": rec["company_value"],
            "profit_year": rec["profit_year"],
            "n_vehicles": rec["n_vehicles"],
            "n_stations": rec["n_stations"],
            "money": rec["money"],
            "n_events": len(events),
            "builds": builds,
            "rank0": ranks0,
            "refuses": refuses[:40],
            "events": interesting,
        })
    write_json_atomically(out, {"reports": reports})
    # compact stdout
    for r in reports:
        print("=" * 72)
        print(f"{r['arm']} seed={r['seed']} value={r['company_value']} "
              f"pyear={r['profit_year']} veh={r['n_vehicles']} stn={r['n_stations']} "
              f"cash={r['money']} events={r['n_events']}")
        print("-- rank0 --")
        for e in r["rank0"]:
            f = e["fields"]
            print(f"  {e['date']} mode={f.get('mode')} kind={f.get('kind')} "
                  f"src={f.get('src')} dst={f.get('dst')} dist={f.get('dist')} "
                  f"profit={f.get('profit')} cost={f.get('cost')} roi={f.get('roi')}")
        print("-- builds/chosen --")
        for e in r["builds"]:
            print(f"  {e['date']} {e['kind']} {e['raw'][20:200]}")
        print("-- first 12 refuses --")
        for e in r["refuses"][:12]:
            print(f"  {e['date']} {e['kind']} {e['raw'][20:200]}")


if __name__ == "__main__":
    main()
