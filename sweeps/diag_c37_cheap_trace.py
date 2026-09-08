"""Sonde C37 road_cheap_trace : L Manhattan avant plan route, graines 7 et 2026.

Témoin : air_cheap_site=1 (le crash TRACEX de la 7).
Test   : air_cheap_site=1 + road_cheap_trace=1.
keep() rend un tuple. script=4 pour le journal de decision.
"""
import argparse
import json
import re
import sys
from pathlib import Path

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
    summarise,
    write_json_atomically,
)
import bench_v2
import openttdlab

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
SEEDS = (7, 2026)
ARMS = (
    "OpexAI[air_cheap_site=1,decision_log=1]",
    "OpexAI[air_cheap_site=1,road_pax_overlap=1,decision_log=1]",
)
KINDS = (
    "AIR_BUILD", "AIR_PLAN_PERF", "AIR_PLAN_INPUT",
    "PORTFOLIO_RANK", "PROJECT_CHOSEN", "PROJECT_DISCARD",
    "ROAD_BUILD", "TASK", "REPORT", "SETTINGS", "CHEAP_TRACE",
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    out = args.out if args.out is not None else (
        ROOT / "results" / (
            f"diag_c37_cheap_trace_{args.years}y_s"
            + "-".join(str(s) for s in args.seeds)
            + ".json"
        )
    )
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(list(ARMS))
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
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
        builds = [e for e in events if e["kind"] in ("AIR_BUILD", "PROJECT_CHOSEN", "ROAD_BUILD")]
        ranks0 = [
            e for e in interesting
            if e["kind"] == "PORTFOLIO_RANK" and e["fields"].get("rank") == "0"
        ]
        refuses = [e for e in events if e["kind"] == "PROJECT_DISCARD"]
        cheapx = [e for e in refuses if e["fields"].get("detail") == "CHEAPX"]
        tracex = [
            e for e in refuses
            if e["fields"].get("detail") in ("TRACEX", "DEPOTX")
        ]
        air_builds = [e for e in events if e["kind"] == "AIR_BUILD"]
        reports.append({
            "arm": rec["arm"],
            "seed": rec["seed"],
            "company_value": rec["company_value"],
            "profit_year": rec["profit_year"],
            "n_vehicles": rec["n_vehicles"],
            "n_stations": rec["n_stations"],
            "money": rec["money"],
            "run_ok": rec["run_ok"],
            "n_events": len(events),
            "n_air_build": len(air_builds),
            "first_air": air_builds[0]["date"] if air_builds else None,
            "second_air": air_builds[1]["date"] if len(air_builds) > 1 else None,
            "n_cheapx": len(cheapx),
            "n_tracex": len(tracex),
            "builds": builds,
            "rank0": ranks0,
            "refuses": refuses[:80],
            "events": interesting,
        })
    write_json_atomically(out, {"reports": reports, "arms": list(ARMS), "seeds": list(args.seeds)})
    for r in reports:
        print("=" * 72)
        print(f"{r['arm']} seed={r['seed']} value={r['company_value']} "
              f"pyear={r['profit_year']} veh={r['n_vehicles']} stn={r['n_stations']} "
              f"air={r['n_air_build']} first={r['first_air']} second={r['second_air']} "
              f"CHEAPX={r['n_cheapx']} TRACEX={r['n_tracex']}")
        print("-- rank0 through 1971-09 --")
        for e in r["rank0"]:
            if e["date"] > "1971-09-30":
                break
            f = e["fields"]
            print(f"  {e['date']} mode={f.get('mode')} dist={f.get('dist')} "
                  f"roi={f.get('roi')} profit={f.get('profit')} cargo={f.get('cargo')}")
        print("-- chosen/air/road through 1971-09 --")
        for e in r["builds"]:
            if e["date"] > "1971-09-30":
                continue
            print(f"  {e['date']} {e['kind']} {e['raw'][20:200]}")
        print("-- SETTINGS / CHEAP_TRACE --")
        for e in r["events"]:
            if e["kind"] in ("SETTINGS", "CHEAP_TRACE"):
                print(f"  {e['date']} {e['kind']} {e['raw'][20:200]}")
        print("-- CHEAPX / TRACEX --")
        for e in r["refuses"]:
            det = e["fields"].get("detail")
            if det in ("CHEAPX", "TRACEX", "DEPOTX", "VOIRIEX"):
                print(f"  {e['date']} {e['raw'][20:200]}")


if __name__ == "__main__":
    main()
