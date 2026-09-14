"""Diagnostic cible des projets bus pax d'extension (OpenTTD 15.3)."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
STARTING_YEAR = 1970
OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def parse_log(output):
    events = []
    candidates = Counter()
    scan_results = Counter()
    town_growth_builds = 0
    road_builds = 0
    road_pax_builds = 0
    for line in (output or "").splitlines():
        match = OPEX_EVENT_RE.search(line)
        if not match:
            continue
        if match.group(4) == "ROAD_BUILD":
            road_builds += 1
        if match.group(4) == "TOWN_GROWTH" and "action=build" in match.group(5):
            town_growth_builds += 1
        if match.group(4) == "ROAD_EXTENSION_CANDIDATE":
            fields = dict(token.split("=", 1) for token in match.group(5).split() if "=" in token)
            candidates[fields.get("type", "unknown")] += 1
        if match.group(4) == "ROAD_EXTENSION_SCAN":
            fields = dict(token.split("=", 1) for token in match.group(5).split() if "=" in token)
            scan_results[fields.get("result", "unknown")] += 1
        if match.group(4) == "PROJECT_CHOSEN" and "mode=road" in match.group(5) and "kind=pax" in match.group(5):
            road_pax_builds += 1
        if match.group(4) != "ROAD_EXTENSION":
            continue
        fields = {}
        for token in match.group(5).split():
            if "=" in token:
                key, value = token.split("=", 1)
                fields[key] = value
        events.append(fields)
    return events, candidates, scan_results, town_growth_builds, road_builds, road_pax_builds


def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    extensions, candidates, scan_results, town_growth_builds, road_builds, road_pax_builds = parse_log(row.get("output", ""))
    kinds = Counter(event.get("type", "unknown") for event in extensions)
    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value", 0),
        "performance_history": last_closed.get("performance_history", 0),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "road_builds": road_builds,
        "road_pax_builds": road_pax_builds,
        "town_growth_builds": town_growth_builds,
        "extension_candidates": dict(candidates),
        "extension_scan_results": dict(scan_results),
        "extensions": len(extensions),
        "extension_types": dict(kinds),
        "extension_events": extensions,
    },)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_bus_extensions_6y_5seeds.json")
    parser.add_argument("--feeder-candidates", type=int, choices=(0, 1), default=1)
    parser.add_argument("--road-stop-houses", type=int, default=10)
    parser.add_argument("--road-pax-focus", action="store_true",
                        help="Ferme les bandes air/rail pour exercer bus_pax_extension")
    args = parser.parse_args()

    params = [("road_pax_build", 1), ("road_pax_extensions", 1),
              ("feeder_candidates", args.feeder_candidates),
              ("road_stop_catchment_houses", args.road_stop_houses), ("decision_log", 1)]
    if args.road_pax_focus:
        params.extend((("air_max_distance", 1), ("rail_min_distance", 40)))
    params = tuple(params)
    arm_name = ("OpexAI[road_pax_build=1,road_pax_extensions=1,feeder_candidates="
                f"{args.feeder_candidates},road_stop_catchment_houses={args.road_stop_houses},decision_log=1]")
    arm = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", params)
    experiments = [{
        "seed": seed,
        "days": 365 * args.years,
        "openttd_config": make_cfg(STARTING_YEAR),
        "ais": (arm,),
        "bench_arm": arm_name,
    } for seed in args.seeds]

    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=3,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    finals = []
    for seed in args.seeds:
        seed_rows = [row for row in rows if row["seed"] == seed]
        if seed_rows:
            finals.append(max(seed_rows, key=lambda row: row["date"]))
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "arm": arm_name,
        "finals": finals,
        "totals": dict(Counter(
            kind for row in finals for kind, count in row["extension_types"].items()
            for _ in range(count)
        )),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["totals"], sort_keys=True))
    print(f"ecrit {args.out}")


if __name__ == "__main__":
    main()
