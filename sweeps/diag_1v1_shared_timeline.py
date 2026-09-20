"""Duel partage OpexAI vs AAAHogEx, chronologie mensuelle et decisions detaillees.

Le duel partage est volontairement un diagnostic narratif, pas un banc de valeur : les deux IA
se disputent le terrain et `decision_log=1` consomme des opcodes chez Opex. Il repond a « qui
construit quoi pendant que l'autre travaille ? », complete par les chunks mensuels et les traces
de construction d'AAAHogEx.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from diag_1v1_monthly import station_detail, vehicle_breakdown

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""
SCRIPT_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[\w\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
HOG_DATE_RE = re.compile(r"^(\d+)-(\d+)-(\d+) (.*)$")
HOG_KEEP = ("# RouteBuilder Start", "# RouteBuilder Succeeded", "# RouteBuilder Failed",
            "Build succeeded(TestMode) AirStation", "HgStation.BuildExec succeeded.AirStation",
            "HgStation.BuildExec failed", "#### TryBuild")


def keep(row):
    chunks = row.get("chunks", {})
    companies = []
    for owner, arm in ((0, "OpexAI"), (1, "AAAHogEx")):
        player = (chunks.get("PLYR", {}).get(owner) or chunks.get("PLYR", {}).get(str(owner)) or {})
        closed = player.get("old_economy") or []
        last = closed[0] if closed else {}
        companies.append({
            "arm": arm, "owner": owner, "money": player.get("money"),
            "current_loan": player.get("current_loan"),
            "company_value": last.get("company_value"),
            "profit_year": last.get("income", 0) + last.get("expenses", 0),
            "vehicles": vehicle_breakdown(chunks, owner), "stations": station_detail(chunks, owner),
        })
    return ({"seed": row["experiment"]["seed"], "date": str(row["date"]),
             "companies": companies,
             "signs": [s.get("name", "") for s in chunks.get("SIGN", {}).values()],
             "output": row.get("output", "")},)


def parse_timeline(output):
    events = []
    for line in (output or "").splitlines():
        sm = SCRIPT_RE.search(line)
        if not sm:
            continue
        owner, text = int(sm.group(1)), sm.group(2).strip()
        if owner == 0:
            om = OPEX_RE.match(text)
            if om:
                year, month, day, kind, detail = om.groups()
                events.append({"arm": "OpexAI", "date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
                               "kind": kind, "detail": detail})
        elif owner == 1:
            hm = HOG_DATE_RE.match(text)
            if hm and any(marker in hm.group(4) for marker in HOG_KEEP):
                year, month, day, detail = hm.groups()
                kind = "AIR" if "AirRoute" in detail or "AirStation" in detail else "BUILD"
                events.append({"arm": "AAAHogEx", "date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
                               "kind": kind, "detail": detail})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_1v1_shared_timeline_2y_seed42.json")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                        (("decision_log", 1), ("probe_scheduler", 1), ("probe_cost", 1)))
    hogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=tuple({"seed": seed, "days": 365 * args.years, "openttd_config": CFG,
                           "ais": (opex, hogex)} for seed in args.seeds),
        max_workers=1, result_processor=keep,
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    by_seed = {}
    for seed in args.seeds:
        seed_rows = sorted((row for row in rows if row["seed"] == seed), key=lambda r: r["date"])
        final = seed_rows[-1]
        by_seed[str(seed)] = {"runs": [{k: v for k, v in row.items() if k != "output"} for row in seed_rows],
                              "timeline": parse_timeline(final["output"]), "final_signs": final["signs"]}
    payload = {"openttd_version": OPENTTD_VERSION, "seeds": args.seeds, "years": args.years,
               "shared_game": True, "instrumented": True, "openttd_config": CFG,
               "by_seed": by_seed}
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"ecrit {args.out}: {sum(len(run['timeline']) for run in by_seed.values())} evenements")


if __name__ == "__main__":
    main()
