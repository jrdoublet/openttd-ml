"""Diagnostic C53 : Mesure comparative des ordres de vehicules reels (chunk ORDL).

Ce script extrait les listes d'ordres reelles associees aux vehicules du chunk VEHS
dans les sauvegardes OpenTTD 15.3, et analyse les distributions de :
1. Drapeaux de non-stop : ONSF_STOP_EVERYWHERE (0) vs ONSF_NO_STOP_AT_INTERMEDIATE_STATIONS (1, OF_NON_STOP_INTERMEDIATE)
2. Drapeaux de chargement : LOAD_IF_POSSIBLE (0), FULL_LOAD_ALL (1), NO_LOAD (2), FULL_LOAD_ANY (3, OF_FULL_LOAD_ANY)
3. Drapeaux de dechargement : UNLOAD_IF_POSSIBLE (0), UNLOAD (1), TRANSFER (2), NO_UNLOAD (4)
4. Ordres de maintenance depot : SERVICE_IF_NEEDED, STOP_IN_DEPOT
5. Longueur et composition des boucles d'ordres par mode de transport (train, road, aircraft, ship).
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
DEFAULT_YEARS = 6
STARTING_YEAR = 1970
DEFAULT_ARMS = ("OpexAI", "AAAHogEx")

TYPE_TO_MODE = {0: "train", 1: "road", 2: "ship", 3: "aircraft"}
TYPE_TO_NAME = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}

# Decodage binaire conforme a src/order_base.h d'OpenTTD
ORDER_TYPE_NAMES = {
    0: "NOTHING",
    1: "GOTO_STATION",
    2: "GOTO_DEPOT",
    3: "LOADING",
    4: "LEAVESTATION",
    5: "DUMMY",
    6: "GOTO_WAYPOINT",
    7: "CONDITIONAL",
    8: "IMPLICIT",
}

NON_STOP_NAMES = {
    0: "STOP_EVERYWHERE",
    1: "NON_STOP_INTERMEDIATE",
    2: "NON_STOP_DESTINATION",
    3: "NON_STOP_ANY",
}

LOAD_TYPE_NAMES = {
    0: "LOAD_IF_POSSIBLE",
    1: "FULL_LOAD_ALL",
    2: "FULL_LOAD",
    3: "FULL_LOAD_ANY",
    4: "NO_LOAD",
}

UNLOAD_TYPE_NAMES = {
    0: "UNLOAD_IF_POSSIBLE",
    1: "UNLOAD",
    2: "TRANSFER",
    4: "NO_UNLOAD",
}


def _first(val):
    return val[0] if isinstance(val, list) and val else val


def decode_order(order_dict):
    """Decode un dictionnaire d'ordre brut d'OpenTTD 15.3 (chunk ORDL)."""
    raw_type = order_dict.get("type", 0)
    raw_flags = order_dict.get("flags", 0)
    dest = order_dict.get("dest", -1)

    # type (uint8) : bits 0-3 = order_type, bits 6-7 = non_stop
    order_type_id = raw_type & 0x0F
    non_stop_id = (raw_type >> 6) & 0x03

    # flags (uint8) : bits 0-2 = unload_type, bits 4-6 = load_type
    unload_type_id = raw_flags & 0x07
    load_type_id = (raw_flags >> 4) & 0x07

    return {
        "raw_type": raw_type,
        "raw_flags": raw_flags,
        "dest": dest,
        "order_type": ORDER_TYPE_NAMES.get(order_type_id, f"UNKNOWN_{order_type_id}"),
        "non_stop": NON_STOP_NAMES.get(non_stop_id, f"UNKNOWN_{non_stop_id}"),
        "is_non_stop": non_stop_id == 1,
        "unload_type": UNLOAD_TYPE_NAMES.get(unload_type_id, f"OTHER_{unload_type_id}"),
        "load_type": LOAD_TYPE_NAMES.get(load_type_id, f"OTHER_{load_type_id}"),
        "is_full_load": load_type_id in (1, 2, 3),
        "is_no_load": load_type_id == 4,
    }


def extract_orders_from_chunks(chunks, target_owner=0):
    """Extrait et classe les ordres des vehicules par mode."""
    ordl = chunks.get("ORDL", {})
    vehs = chunks.get("VEHS", {})

    vehicle_orders_by_mode = defaultdict(list)
    stats_by_mode = defaultdict(lambda: {
        "n_vehicles": 0,
        "n_orders_total": 0,
        "n_station_orders": 0,
        "n_non_stop_station_orders": 0,
        "n_full_load_orders": 0,
        "n_no_load_orders": 0,
        "n_transfer_orders": 0,
        "n_depot_orders": 0,
        "chain_lengths": [],
        "order_type_counts": Counter(),
        "load_type_counts": Counter(),
        "unload_type_counts": Counter(),
        "non_stop_counts": Counter(),
        "raw_type_flags_counts": Counter(),
    })

    iterator = vehs.items() if isinstance(vehs, dict) else enumerate(vehs)
    for vid, vdata in iterator:
        if not isinstance(vdata, dict):
            continue
        vtype = vdata.get("type")
        if vtype not in TYPE_TO_MODE:
            continue
        mode = TYPE_TO_MODE[vtype]
        subname = TYPE_TO_NAME[str(vtype)]
        sub = _first(vdata.get(subname))
        if not isinstance(sub, dict):
            continue
        common = _first(sub.get("common"))
        if not isinstance(common, dict):
            continue

        owner = common.get("owner")
        if owner is not None and owner != target_owner:
            continue

        orders_idx = common.get("orders")
        if orders_idx is None or orders_idx <= 0 or orders_idx == 65535 or orders_idx == -1:
            continue

        # OpenTTD serialise les pointeurs de pool d'ordres avec 0 = nullptr et 1..N = index + 1
        ordl_key = str(orders_idx - 1)
        entry = _first(ordl.get(ordl_key)) if isinstance(ordl, dict) else None
        if not isinstance(entry, dict):
            continue

        raw_orders_list = entry.get("orders", [])
        decoded_orders = [decode_order(o) for o in raw_orders_list if isinstance(o, dict)]

        st = stats_by_mode[mode]
        st["n_vehicles"] += 1
        st["n_orders_total"] += len(decoded_orders)
        st["chain_lengths"].append(len(decoded_orders))

        for o in decoded_orders:
            st["raw_type_flags_counts"][(o["raw_type"], o["raw_flags"])] += 1
            st["order_type_counts"][o["order_type"]] += 1
            st["non_stop_counts"][o["non_stop"]] += 1
            st["load_type_counts"][o["load_type"]] += 1
            st["unload_type_counts"][o["unload_type"]] += 1

            if o["order_type"] == "GOTO_STATION":
                st["n_station_orders"] += 1
                if o["is_non_stop"]:
                    st["n_non_stop_station_orders"] += 1
                if o["is_full_load"]:
                    st["n_full_load_orders"] += 1
                if o["is_no_load"]:
                    st["n_no_load_orders"] += 1
                if o["unload_type"] == "TRANSFER":
                    st["n_transfer_orders"] += 1
            elif o["order_type"] == "GOTO_DEPOT":
                st["n_depot_orders"] += 1

        vehicle_orders_by_mode[mode].append({
            "vehicle_id": str(vid),
            "order_list_idx": orders_idx,
            "orders": decoded_orders,
        })

    # Conversion des counters en dictionnaires serialisables
    formatted_stats = {}
    for mode, st in stats_by_mode.items():
        n_st = st["n_station_orders"]
        lengths = st["chain_lengths"]
        formatted_stats[mode] = {
            "n_vehicles": st["n_vehicles"],
            "n_orders_total": st["n_orders_total"],
            "n_station_orders": n_st,
            "n_non_stop_station_orders": st["n_non_stop_station_orders"],
            "pct_non_stop_station_orders": (st["n_non_stop_station_orders"] / n_st * 100.0) if n_st > 0 else 0.0,
            "n_full_load_orders": st["n_full_load_orders"],
            "pct_full_load_station_orders": (st["n_full_load_orders"] / n_st * 100.0) if n_st > 0 else 0.0,
            "n_no_load_orders": st["n_no_load_orders"],
            "pct_no_load_station_orders": (st["n_no_load_orders"] / n_st * 100.0) if n_st > 0 else 0.0,
            "n_transfer_orders": st["n_transfer_orders"],
            "n_depot_orders": st["n_depot_orders"],
            "mean_chain_length": statistics.mean(lengths) if lengths else 0.0,
            "order_type_counts": dict(st["order_type_counts"]),
            "non_stop_counts": dict(st["non_stop_counts"]),
            "load_type_counts": dict(st["load_type_counts"]),
            "unload_type_counts": dict(st["unload_type_counts"]),
            "raw_type_flags_counts": {f"({k[0]},{k[1]})": v for k, v in st["raw_type_flags_counts"].items()},
        }

    return formatted_stats


def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    py = year_profit(closed)

    order_stats = extract_orders_from_chunks(chunks, target_owner=0)

    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "order_stats": order_stats,
    },)


def run_selftest():
    """Selftest pur Python : verifie le decodage conforme du chunk ORDL."""
    test_orders = {
        "ord_opex_pax": {"type": 33, "flags": 0, "dest": 10},       # GOTO_STATION, STOP_EVERYWHERE, LOAD_IF_POSSIBLE
        "ord_opex_freight": {"type": 33, "flags": 48, "dest": 11},   # GOTO_STATION, STOP_EVERYWHERE, FULL_LOAD_ANY (48=0x30)
        "ord_aaa_road_src": {"type": 97, "flags": 48, "dest": 20},   # GOTO_STATION, NON_STOP_INTERMEDIATE (97=33+64), FULL_LOAD_ANY
        "ord_aaa_road_dst": {"type": 97, "flags": 66, "dest": 21},   # GOTO_STATION, NON_STOP_INTERMEDIATE, TRANSFER(2) | NO_LOAD(64)
        "ord_aaa_depot": {"type": 66, "flags": 2, "dest": 5},        # GOTO_DEPOT(2) + NON_STOP_INTERMEDIATE(64), SERVICE_IF_NEEDED(2)
    }

    d1 = decode_order(test_orders["ord_opex_pax"])
    assert d1["order_type"] == "GOTO_STATION"
    assert d1["non_stop"] == "STOP_EVERYWHERE"
    assert not d1["is_non_stop"]
    assert d1["load_type"] == "LOAD_IF_POSSIBLE"
    assert not d1["is_full_load"]

    d2 = decode_order(test_orders["ord_opex_freight"])
    assert d2["order_type"] == "GOTO_STATION"
    assert not d2["is_non_stop"]
    assert d2["load_type"] == "FULL_LOAD_ANY"
    assert d2["is_full_load"]

    d3 = decode_order(test_orders["ord_aaa_road_src"])
    assert d3["order_type"] == "GOTO_STATION"
    assert d3["non_stop"] == "NON_STOP_INTERMEDIATE"
    assert d3["is_non_stop"]
    assert d3["is_full_load"]

    d4 = decode_order(test_orders["ord_aaa_road_dst"])
    assert d4["order_type"] == "GOTO_STATION"
    assert d4["is_non_stop"]
    assert d4["unload_type"] == "TRANSFER"
    assert d4["is_no_load"]

    d5 = decode_order(test_orders["ord_aaa_depot"])
    assert d5["order_type"] == "GOTO_DEPOT"
    assert d5["is_non_stop"]

    # Test d'extraction complet avec faux chunks
    fake_chunks = {
        "ORDL": {
            "100": {"orders": [test_orders["ord_aaa_road_src"], test_orders["ord_aaa_road_dst"]]},
            "101": {"orders": [test_orders["ord_opex_pax"], test_orders["ord_opex_freight"]]},
        },
        "VEHS": {
            "1": {"type": 1, "roadveh": [{"common": {"owner": 0, "orders": 101}}]},
            "2": {"type": 0, "train": [{"common": {"owner": 0, "orders": 102}}]},
        }
    }
    stats = extract_orders_from_chunks(fake_chunks, target_owner=0)
    assert stats["road"]["n_vehicles"] == 1
    assert stats["road"]["n_station_orders"] == 2
    assert stats["road"]["pct_non_stop_station_orders"] == 100.0
    assert stats["road"]["pct_full_load_station_orders"] == 50.0
    assert stats["road"]["pct_no_load_station_orders"] == 50.0

    assert stats["train"]["n_vehicles"] == 1
    assert stats["train"]["n_station_orders"] == 2
    assert stats["train"]["pct_non_stop_station_orders"] == 0.0
    assert stats["train"]["pct_full_load_station_orders"] == 50.0

    print("✅ Selftest diag_c53_orders reussi avec succes (decodage OpenTTD 15.3 valide).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS))
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c53_orders_6y_5seeds.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    enable_savegame_cleanup()

    ai_instances = {}
    for arm in args.arms:
        if arm == "AAAHogEx":
            ai_instances[arm] = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
        elif arm == "OpexAI":
            ai_instances[arm] = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ())
        elif arm.startswith("OpexAI[") and arm.endswith("]"):
            # Parser les reglages comme key=value
            inside = arm[len("OpexAI["):-1]
            kvs = []
            for pair in inside.split(","):
                k, v = pair.split("=")
                kvs.append((k.strip(), int(v.strip())))
            ai_instances[arm] = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", tuple(kvs))
        else:
            raise ValueError(f"Arm non reconnu : {arm}")

    experiments = []
    days = 365 * args.years
    cfg = make_cfg(STARTING_YEAR)

    for arm in args.arms:
        ai = ai_instances[arm]
        for seed in args.seeds:
            experiments.append({
                "bench_arm": arm,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (ai,),
            })

    print(f"=== Lancement du diagnostic C53 : {len(args.arms)} bras x {len(args.seeds)} graines x {args.years} ans ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=keep,
        experiments=experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        )
    ))

    # Deduplication : ne conserver que le dernier autosave de chaque partie
    by_run = {}
    for r in rows:
        key = (r["arm"], r["seed"])
        by_run.setdefault(key, []).append(r)

    final_rows = []
    for key, series in sorted(by_run.items()):
        series.sort(key=lambda item: item.get("date", ""))
        final_rows.append(series[-1])

    # Agregation des resultats
    results_by_arm = defaultdict(list)
    for r in final_rows:
        results_by_arm[r["arm"]].append(r)

    print("\n" + "=" * 90)
    print(f"{'Arm':28} | {'Seed':6} | {'Valeur (£)':>12} | {'Profit/an (£)':>14} | {'Vehs':>5} | {'Gares':>5}")
    print("-" * 90)
    for arm in args.arms:
        for r in results_by_arm[arm]:
            print(f"{r['arm']:28} | {r['seed']:6d} | {r['company_value']:>12,d} | {r['profit_year']:>14,d} | {r['n_vehicles']:>5d} | {r['n_stations']:>5d}")
        print("-" * 90)

    print("\n=== SYNTHÈSE DES ORDRES PAR BRAS ET PAR MODE (ÉTAT FINAL) ===")
    summary_by_arm = {}
    for arm in args.arms:
        arm_rows = results_by_arm[arm]
        summary_by_arm[arm] = {}
        print(f"\n--- Bras : {arm} ---")
        modes = ("aircraft", "road", "train", "ship")
        for mode in modes:
            vehs_tot = sum(r["order_stats"].get(mode, {}).get("n_vehicles", 0) for r in arm_rows)
            st_orders_tot = sum(r["order_stats"].get(mode, {}).get("n_station_orders", 0) for r in arm_rows)
            ns_orders_tot = sum(r["order_stats"].get(mode, {}).get("n_non_stop_station_orders", 0) for r in arm_rows)
            fl_orders_tot = sum(r["order_stats"].get(mode, {}).get("n_full_load_orders", 0) for r in arm_rows)
            nl_orders_tot = sum(r["order_stats"].get(mode, {}).get("n_no_load_orders", 0) for r in arm_rows)
            depot_orders_tot = sum(r["order_stats"].get(mode, {}).get("n_depot_orders", 0) for r in arm_rows)

            pct_ns = (ns_orders_tot / st_orders_tot * 100.0) if st_orders_tot > 0 else 0.0
            pct_fl = (fl_orders_tot / st_orders_tot * 100.0) if st_orders_tot > 0 else 0.0
            pct_nl = (nl_orders_tot / st_orders_tot * 100.0) if st_orders_tot > 0 else 0.0

            summary_by_arm[arm][mode] = {
                "vehicles_total": vehs_tot,
                "station_orders_total": st_orders_tot,
                "pct_non_stop": pct_ns,
                "pct_full_load": pct_fl,
                "pct_no_load": pct_nl,
                "depot_orders_total": depot_orders_tot,
            }

            print(f"  [{mode:8}] Vehs: {vehs_tot:>4d} | Gares: {st_orders_tot:>5d} | "
                  f"Non-Stop: {pct_ns:>5.1f}% | FullLoad: {pct_fl:>5.1f}% | "
                  f"NoLoad: {pct_nl:>5.1f}% | Depot: {depot_orders_tot:>4d}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "years": args.years,
        "seeds": args.seeds,
        "arms": list(args.arms),
        "summary_by_arm": summary_by_arm,
        "final_rows": final_rows,
        "all_rows": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"\nRapport complet écrit dans {args.out}")


if __name__ == "__main__":
    main()
