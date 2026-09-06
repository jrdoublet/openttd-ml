"""Diagnostic pax voirie : pourquoi les gares tombent de ~96 a ~48.

Temoin : overlap=0 voirie=0 (cul-de-sac historique).
Test   : overlap=0 voirie=1 (voirie seule, le bras R01 du banc de nuit).
keep() rend un tuple. script=4 pour VOIRIE_PLAN / TOWN_GROWTH / ROAD_BUILD.
"""
import argparse
from collections import Counter
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
SEEDS = (7, 42)
ARMS = (
    "OpexAI[road_pax_overlap=0,road_pax_voirie=0,decision_log=1]",
    "OpexAI[road_pax_overlap=0,road_pax_voirie=1,decision_log=1]",
)
KINDS = (
    "SETTINGS", "VOIRIE_PLAN", "TOWN_GROWTH", "ROAD_BUILD", "PROJECT_CHOSEN",
    "PROJECT_DISCARD", "AIR_BUILD", "REPORT",
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
            "raw": m.group(0)[:280],
        })
    return events


def summarise_report(rec):
    events = parse_events(rec.get("openttd_output"))
    rec["openttd_output"] = ""
    interesting = [e for e in events if e["kind"] in KINDS]
    discards = [e for e in events if e["kind"] == "PROJECT_DISCARD"]
    voirie = [e for e in events if e["kind"] == "VOIRIE_PLAN"]
    growth = [e for e in events if e["kind"] == "TOWN_GROWTH"]
    roads = [e for e in events if e["kind"] == "ROAD_BUILD"]
    chosen_road = [
        e for e in events
        if e["kind"] == "PROJECT_CHOSEN" and e["fields"].get("mode") == "road"
    ]
    fail_detail = Counter()
    for e in discards:
        det = e["fields"].get("detail") or e["fields"].get("reason") or "?"
        fail_detail[det] += 1
    voirie_fail = Counter(e["fields"].get("fail", "ok") for e in voirie)
    voirie_via = Counter(e["fields"].get("via", "-") for e in voirie if e["fields"].get("ok") == "1")
    growth_action = Counter(e["fields"].get("action", "?") for e in growth)
    growth_reason = Counter()
    for e in growth:
        if e["fields"].get("action") == "fail":
            growth_reason[e["fields"].get("reason", "?") + ":" + (e["fields"].get("detail") or "-")] += 1
    return {
        "arm": rec["arm"],
        "seed": rec["seed"],
        "company_value": rec["company_value"],
        "profit_year": rec["profit_year"],
        "performance_history": rec.get("performance_history"),
        "median_station_rating": rec.get("median_station_rating"),
        "n_vehicles": rec["n_vehicles"],
        "n_stations": rec["n_stations"],
        "run_ok": rec["run_ok"],
        "n_events": len(events),
        "n_road_build": len(roads),
        "n_road_chosen": len(chosen_road),
        "n_town_growth": growth_action.get("build", 0),
        "n_town_growth_fail": sum(v for k, v in growth_action.items() if k == "fail"),
        "n_voirie_ok": voirie_fail.get("ok", 0) if "ok" in voirie_fail else sum(
            1 for e in voirie if e["fields"].get("ok") == "1"
        ),
        "n_voirie_events": len(voirie),
        "voirie_fail": dict(voirie_fail),
        "voirie_via": dict(voirie_via),
        "growth_action": dict(growth_action),
        "growth_reason": dict(growth_reason),
        "discard_detail": dict(fail_detail),
        "voirie_ok_sample": [e for e in voirie if e["fields"].get("ok") == "1"][:12],
        "voirie_fail_sample": [e for e in voirie if e["fields"].get("ok") != "1"][:20],
        "growth_fail_sample": [e for e in growth if e["fields"].get("action") == "fail"][:20],
        "growth_ok_sample": [e for e in growth if e["fields"].get("action") == "build"][:12],
        "road_builds": roads[:20],
        "settings": [e for e in events if e["kind"] == "SETTINGS"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    out = args.out if args.out is not None else (
        ROOT / "docs" / (
            f"diag_voirie_bug_{args.years}y_s"
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
    from bench_v2 import summarise
    summary = summarise(rows)
    reports = [summarise_report(rec) for rec in summary]
    write_json_atomically(out, {"reports": reports, "arms": list(ARMS), "seeds": list(args.seeds),
                                "years": args.years})
    for r in reports:
        print("=" * 72)
        print(f"{r['arm']} seed={r['seed']} value={r['company_value']} "
              f"pyear={r['profit_year']} score={r['performance_history']} "
              f"notes={r['median_station_rating']} veh={r['n_vehicles']} "
              f"stn={r['n_stations']}")
        print(f"  ROAD_BUILD={r['n_road_build']} road_chosen={r['n_road_chosen']} "
              f"TG_ok={r['n_town_growth']} TG_fail={r['n_town_growth_fail']} "
              f"VOIRIE_events={r['n_voirie_events']}")
        print(f"  voirie_fail={r['voirie_fail']} via={r['voirie_via']}")
        print(f"  growth_action={r['growth_action']} growth_reason={r['growth_reason']}")
        print(f"  discard={r['discard_detail']}")
        print("  -- SETTINGS --")
        for e in r["settings"][:2]:
            print(f"    {e['raw'][20:240]}")
        print("  -- VOIRIE fail sample --")
        for e in r["voirie_fail_sample"][:8]:
            print(f"    {e['date']} {e['raw'][20:240]}")
        print("  -- VOIRIE ok sample --")
        for e in r["voirie_ok_sample"][:6]:
            print(f"    {e['date']} {e['raw'][20:240]}")
        print("  -- TOWN_GROWTH fail sample --")
        for e in r["growth_fail_sample"][:8]:
            print(f"    {e['date']} {e['raw'][20:240]}")
        print("  -- TOWN_GROWTH ok sample --")
        for e in r["growth_ok_sample"][:6]:
            print(f"    {e['date']} {e['raw'][20:240]}")


if __name__ == "__main__":
    main()
