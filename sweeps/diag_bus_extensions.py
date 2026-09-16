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
from diag_c53_orders import decode_order

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


def _first(value):
    return value[0] if isinstance(value, list) and value else value


def inspect_extended_feeder_orders(chunks):
    """Inspecte directement VEHS -> ORDL et déduplique les listes d'ordres partagées.

    Une chaîne feeder bus étendue valide est :
    - au moins trois GOTO_STATION ;
    - ville + tous les arrêts intermédiaires : LOAD_IF_POSSIBLE / NO_UNLOAD ;
    - dernier arrêt (hub) : NO_LOAD / TRANSFER.
    """
    vehs = chunks.get("VEHS", {})
    ordl = chunks.get("ORDL", {})
    seen_order_lists = set()
    chains = []
    errors = []
    iterator = vehs.items() if isinstance(vehs, dict) else enumerate(vehs)
    for vehicle_id, vehicle in iterator:
        if not isinstance(vehicle, dict) or vehicle.get("type") != 1:
            continue
        roadveh = _first(vehicle.get("roadveh"))
        common = _first((roadveh or {}).get("common")) if isinstance(roadveh, dict) else None
        if not isinstance(common, dict) or common.get("owner") != 0:
            continue
        unitnumber = _first(common.get("unitnumber", 0)) or 0
        orders_idx = _first(common.get("orders"))
        if unitnumber <= 0 or not isinstance(orders_idx, int) or orders_idx <= 0:
            continue
        ordl_key = str(orders_idx - 1)
        if ordl_key in seen_order_lists:
            continue
        seen_order_lists.add(ordl_key)
        entry = _first(ordl.get(ordl_key)) if isinstance(ordl, dict) else None
        raw_orders = entry.get("orders") if isinstance(entry, dict) else None
        if not isinstance(raw_orders, list):
            errors.append(f"vehicle={vehicle_id} ordl={ordl_key} unresolved")
            continue
        decoded = [decode_order(order) for order in raw_orders if isinstance(order, dict)]
        station_orders = [order for order in decoded if order["order_type"] == "GOTO_STATION"]
        if len(station_orders) < 3:
            continue
        city_orders = station_orders[:-1]
        hub = station_orders[-1]
        city_ok = all(
            order["load_type"] == "LOAD_IF_POSSIBLE"
            and order["unload_type"] == "NO_UNLOAD"
            for order in city_orders
        )
        hub_ok = hub["load_type"] == "NO_LOAD" and hub["unload_type"] == "TRANSFER"
        if city_ok or hub_ok:
            chains.append({
                "vehicle_id": str(vehicle_id),
                "unitnumber": unitnumber,
                "order_list_idx": orders_idx,
                "station_orders": station_orders,
                "city_intermediate_ok": city_ok,
                "hub_ok": hub_ok,
                "strict_extended_feeder": city_ok and hub_ok,
            })
    return {
        "chains": chains,
        "errors": errors,
        "strict_extended_feeders": sum(chain["strict_extended_feeder"] for chain in chains),
        "invalid_extended_feeders": sum(not chain["strict_extended_feeder"] for chain in chains),
    }


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
    feeder_orders = inspect_extended_feeder_orders(chunks)
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
        "feeder_order_invariants": feeder_orders,
    },)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_bus_extensions_6y_5seeds.json")
    parser.add_argument("--feeder-candidates", type=int, choices=(0, 1), default=1)
    parser.add_argument("--feeder-hub-check", type=int, choices=(0, 1), default=0,
                        help="0 force le chemin feeder pour le diagnostic structurel")
    parser.add_argument("--feeder-mail-duplicate", type=int, choices=(0, 1), default=0,
                        help="0 isole les bus feeders des duplications courrier")
    parser.add_argument("--road-stop-houses", type=int, default=10)
    parser.add_argument("--road-pax-focus", action="store_true",
                        help="Ferme les bandes air/rail pour exercer bus_pax_extension")
    args = parser.parse_args()

    params = [("road_pax_build", 1), ("road_pax_extensions", 1),
              ("feeder_candidates", args.feeder_candidates),
              ("feeder_hub_check", args.feeder_hub_check),
              ("feeder_mail_duplicate", args.feeder_mail_duplicate),
              ("road_stop_catchment_houses", args.road_stop_houses), ("decision_log", 1)]
    if args.road_pax_focus:
        params.extend((("air_max_distance", 1), ("rail_min_distance", 40)))
    params = tuple(params)
    arm_name = ("OpexAI[road_pax_build=1,road_pax_extensions=1,feeder_candidates="
                f"{args.feeder_candidates},feeder_hub_check={args.feeder_hub_check},"
                f"feeder_mail_duplicate={args.feeder_mail_duplicate},"
                f"road_stop_catchment_houses={args.road_stop_houses},decision_log=1]")
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
        max_workers=args.workers,
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
