"""Sonde C35.4 : journaux de decision sur graines faibles vs fortes.

Bras : defaut contre shadow_pricing=1, les deux en decision_log=1.
script=4. keep() rend un tuple. Lecture PLYR.old_economy.
"""
import argparse
from collections import Counter, defaultdict
import json
import re
import sys
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
    make_cfg,
    quarter_profit,
    year_profit,
    write_json_atomically,
)
import bench_v2

ARMS = (
    "OpexAI[decision_log=1]",
    "OpexAI[shadow_pricing=1,decision_log=1]",
)
SEEDS = (123456, 1024, 7, 8675309)
YEARS = 3

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
KEEP_KINDS = {
    "SHADOW_PRICES", "PORTFOLIO_RANK", "PROJECT_CHOSEN",
    "AIR_BUILD", "ROAD_BUILD", "RAIL_BUILD", "FEEDER_BUILD", "WATER_BUILD",
    "AIR_FLEET", "KS_POOL", "KS_CAND", "PROJECT_DISCARD", "TRACEX", "ABND",
}


def parse_fields(rest):
    fields = {}
    for tok in (rest or "").split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            fields[k] = v
    return fields


def parse_events(output):
    events = []
    kinds = Counter()
    for line in (output or "").splitlines():
        m = OPEX_RE.search(line)
        if not m:
            continue
        y, mo, d, kind, rest = m.groups()
        kinds[kind] += 1
        if kind not in KEEP_KINDS:
            continue
        events.append({
            "date": f"{y}-{int(mo):02d}-{int(d):02d}",
            "kind": kind,
            "fields": parse_fields(rest),
        })
    return events, dict(kinds)


def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    events, kinds = parse_events(row.get("output", ""))
    experiment = row["experiment"]
    arm = experiment.get("bench_arm")
    if not arm:
        run = experiment.get("bench_run") or []
        arm = run[0] if run else "unknown"
    return ({
        "arm": arm,
        "seed": experiment["seed"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": year_profit(closed) or 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "money": (player or {}).get("money"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "kinds": kinds,
        "events": events,
    },)


def last_by_run(rows):
    last = {}
    for rec in rows:
        last[(rec["arm"], rec["seed"])] = rec
    return last


def analyse(rec):
    events = rec.get("events") or []
    kinds = rec.get("kinds") or {}
    rank0 = Counter()
    rank0_year = defaultdict(Counter)
    chosen = Counter()
    chosen_year = defaultdict(Counter)
    builds = Counter()
    fleet_grow = 0
    fleet_refuse = 0
    shadows = []
    rank0_rows = []
    chosen_rows = []
    for e in events:
        f = e.get("fields") or {}
        y = e["date"][:4]
        if e["kind"] == "PORTFOLIO_RANK" and f.get("rank") == "0":
            mode = f.get("mode", "?")
            kind = f.get("kind", "?")
            key = f"{mode}/{kind}"
            rank0[key] += 1
            rank0_year[y][key] += 1
            rank0_rows.append({
                "date": e["date"], "mode": mode, "kind": kind,
                "roi": f.get("roi"), "score": f.get("score"),
                "cost": f.get("cost"), "profit": f.get("profit"),
            })
        elif e["kind"] == "PROJECT_CHOSEN":
            mode = f.get("mode", "?")
            kind = f.get("kind", mode)
            key = f"{mode}/{kind}"
            chosen[key] += 1
            chosen_year[y][key] += 1
            chosen_rows.append({
                "date": e["date"], "mode": mode, "kind": kind,
                "roi": f.get("roi"), "cost": f.get("cost"),
                "profit": f.get("profit"), "dist": f.get("dist"),
            })
        elif e["kind"] in ("AIR_BUILD", "ROAD_BUILD", "RAIL_BUILD", "FEEDER_BUILD", "WATER_BUILD"):
            builds[e["kind"]] += 1
        elif e["kind"] == "AIR_FLEET":
            action = f.get("action", "")
            if action == "grow":
                fleet_grow += 1
            elif action == "refuse":
                fleet_refuse += 1
        elif e["kind"] == "SHADOW_PRICES":
            shadows.append({
                "date": e["date"],
                "argent": f.get("lambda_argent"),
                "ops": f.get("lambda_ops"),
                "foncier": f.get("lambda_foncier"),
                "slots_road": f.get("lambda_slots_road"),
                "slots_air": f.get("lambda_slots_air"),
                "slots_rail": f.get("lambda_slots_rail"),
                "b_argent": f.get("b_argent"),
                "b_ops": f.get("b_ops"),
                "b_foncier": f.get("b_foncier"),
            })
    return {
        "kinds": kinds,
        "rank0": dict(rank0),
        "rank0_year": {y: dict(c) for y, c in rank0_year.items()},
        "chosen": dict(chosen),
        "chosen_year": {y: dict(c) for y, c in chosen_year.items()},
        "builds": dict(builds),
        "fleet_grow": fleet_grow,
        "fleet_refuse": fleet_refuse,
        "n_shadow": len(shadows),
        "shadow_head": shadows[:8],
        "shadow_tail": shadows[-8:],
        "rank0_head": rank0_rows[:12],
        "chosen_all": chosen_rows,
        "discards": kinds.get("PROJECT_DISCARD", 0),
        "tracex": kinds.get("TRACEX", 0),
        "abnd": kinds.get("ABND", 0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    out = args.out if args.out is not None else (
        ROOT / "results" / f"diag_c35_4_weak_{args.years}y.json"
    )
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
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
        experiments=experiments(built, list(args.seeds), args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    last = last_by_run(rows)
    reports = {}
    for key, rec in last.items():
        reports[f"{key[0]}|{key[1]}"] = {
            "arm": rec["arm"],
            "seed": rec["seed"],
            "company_value": rec["company_value"],
            "profit_year": rec["profit_year"],
            "n_vehicles": rec["n_vehicles"],
            "n_stations": rec["n_stations"],
            "money": rec["money"],
            "analysis": analyse(rec),
        }
    payload = {
        "years": args.years,
        "seeds": list(args.seeds),
        "arms": list(ARMS),
        "reports": reports,
    }
    write_json_atomically(out, payload)
    print("out", out)
    for seed in args.seeds:
        print(f"\n===== seed {seed} =====")
        for arm in ARMS:
            rec = last.get((arm, seed))
            if rec is None:
                print(f"  MISSING {arm}")
                continue
            a = analyse(rec)
            tag = "def" if "shadow_pricing=1" not in arm else "shd"
            print(f"  {tag}: val={rec['company_value']} py={rec['profit_year']} "
                  f"veh={rec['n_vehicles']} stn={rec['n_stations']} money={rec['money']}")
            print(f"     builds={a['builds']} fleet_grow={a['fleet_grow']} "
                  f"refuse={a['fleet_refuse']} tracex={a['tracex']} abnd={a['abnd']}")
            print(f"     rank0={a['rank0']}")
            print(f"     chosen={a['chosen']}")
            if a["shadow_head"]:
                h = a["shadow_head"][0]
                print(f"     lambda0 argent={h.get('argent')} ops={h.get('ops')} "
                      f"foncier={h.get('foncier')} slots_air={h.get('slots_air')} "
                      f"b_foncier={h.get('b_foncier')} b_argent={h.get('b_argent')}")


if __name__ == "__main__":
    main()
