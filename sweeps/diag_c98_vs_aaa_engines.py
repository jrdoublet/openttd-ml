#!/usr/bin/env python3
"""C98: current-default OpexAI vs AAAHogEx realised AIR engine diagnostic."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from bench_1v1_5y_20seeds import extract_line_telemetry
from physical_counters import decode_vehicles

DEFAULT_SEEDS = (42, 100, 999, 1234, 5678)
PROFIT_RAW_UNITS_PER_GBP = 256.0
KNOWN_ENGINE_NAMES = {"217":"FFP Dart","218":"Yate Haugan","221":"Bakewell Luckett LB-9","223":"Bakewell Luckett LB-10","225":"Yate Aerospace YAC 1-11","227":"Darwin 200","228":"Darwin 300","232":"Guru Galaxy"}


def _first(value):
    return value[0] if isinstance(value, list) and value else value


def _raw_air_common(chunks, vehicle_id):
    vehs = (chunks or {}).get("VEHS") or {}
    record = vehs.get(vehicle_id)
    if record is None:
        record = vehs.get(str(vehicle_id))
    if not isinstance(record, dict) or str(record.get("type")) != "3":
        return None
    body = _first(record.get("aircraft"))
    common = _first((body or {}).get("common")) if isinstance(body, dict) else None
    return common if isinstance(common, dict) else None


def _engine_label(engine):
    key = str(engine)
    return f"{key}:{KNOWN_ENGINE_NAMES.get(key, 'unknown')}"


def aircraft_rows(chunks, owner, snapshot_year):
    decoded = decode_vehicles((chunks or {}).get("VEHS"), target_owner=owner)
    rows = []
    if not decoded.get("chunk_valid"):
        return rows
    for detail in decoded.get("primary_vehicles_detail") or []:
        if detail.get("mode") != "air":
            continue
        common = _raw_air_common(chunks, detail.get("index"))
        if common is None:
            continue
        engine = common.get("engine_type")
        raw_profit = common.get("profit_last_year")
        build_year = common.get("build_year")
        profit = raw_profit / PROFIT_RAW_UNITS_PER_GBP if isinstance(raw_profit, (int, float)) else None
        full_prior_year = isinstance(build_year, int) and build_year <= snapshot_year - 2
        rows.append({
            "vehicle_id": detail.get("index"),
            "engine": engine,
            "engine_label": _engine_label(engine),
            "build_year": build_year,
            "profit_last_year_gbp": profit,
            "full_prior_year": full_prior_year,
            "passenger_capacity": int((detail.get("consist_capacities") or {}).get(0, 0)),
            "book_value": detail.get("consist_value") or 0,
        })
    return rows


def air_lines(chunks, owner, aircraft):
    by_vehicle = {row["vehicle_id"]: row for row in aircraft}
    telemetry = extract_line_telemetry(chunks, owner)
    out = []
    for line in telemetry.get("lines", []):
        if line.get("mode") != "air":
            continue
        full = [by_vehicle[v] for v in line.get("vehicle_ids", [])
                if v in by_vehicle and by_vehicle[v].get("full_prior_year")]
        out.append({
            "service_key": line.get("service_key"),
            "market_key": line.get("market_key"),
            "vehicles": line.get("vehicles", 0),
            "profit_last_year_gbp": line.get("profit_last_year_gbp", 0.0),
            "full_year_vehicles": len(full),
            "full_year_profit_last_year_gbp": sum(
                row.get("profit_last_year_gbp") or 0.0 for row in full
            ),
            "full_year_engines": dict(Counter(row["engine_label"] for row in full)),
        })
    return out


def keep(row):
    date = str(row.get("date", ""))
    match = re.match(r"^(\d{4})-12-", date)
    if not match:
        return ()
    year = int(match.group(1))
    chunks = row.get("chunks") or {}
    companies = {}
    for owner in (0, 1):
        aircraft = aircraft_rows(chunks, owner, year)
        companies[str(owner)] = {
            "aircraft": aircraft,
            "lines": air_lines(chunks, owner, aircraft),
        }
    return ({
        "seed": row.get("experiment", {}).get("seed"),
        "year": year,
        "date": date,
        "companies": companies,
    },)


def _stats(values):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(vals),
        "mean": round(statistics.mean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
    }


def _company_summary(latest, owner):
    rows = []
    for snap in latest.values():
        rows.extend(snap["companies"][str(owner)]["aircraft"])
    full = [row for row in rows if row.get("full_prior_year")]
    by_engine = defaultdict(list)
    for row in full:
        by_engine[row["engine_label"]].append(row)
    return {
        "all_aircraft": len(rows),
        "full_prior_year_aircraft": len(full),
        "profit_last_year_per_plane_gbp": _stats([
            row.get("profit_last_year_gbp") for row in full
        ]),
        "by_engine": {
            engine: {
                "n": len(group),
                "share_pct": round(100.0 * len(group) / len(full), 3) if full else None,
                "profit_last_year_per_plane_gbp": _stats([
                    row.get("profit_last_year_gbp") for row in group
                ]),
                "passenger_capacity": _stats([row.get("passenger_capacity") for row in group]),
            }
            for engine, group in sorted(by_engine.items())
        },
    }


def _aggregate_services(lines):
    services = {}
    for line in lines:
        key = line.get("service_key")
        if not key:
            continue
        item = services.setdefault(key, {
            "vehicles": 0,
            "profit": 0.0,
            "engines": Counter(),
        })
        item["vehicles"] += int(line.get("full_year_vehicles") or 0)
        item["profit"] += float(line.get("full_year_profit_last_year_gbp") or 0.0)
        item["engines"].update(line.get("full_year_engines") or {})
    return services


def _common_market_summary(latest):
    observations = []
    for seed, snap in sorted(latest.items()):
        left = _aggregate_services(snap["companies"]["0"]["lines"])
        right = _aggregate_services(snap["companies"]["1"]["lines"])
        for key in sorted(set(left) & set(right)):
            opex = left[key]
            aaa = right[key]
            if opex["vehicles"] <= 0 or aaa["vehicles"] <= 0:
                continue
            observations.append({
                "seed": seed,
                "service_key": key,
                "opex_vehicles": opex["vehicles"],
                "aaa_vehicles": aaa["vehicles"],
                "opex_profit": opex["profit"],
                "aaa_profit": aaa["profit"],
                "opex_profit_per_plane": opex["profit"] / opex["vehicles"],
                "aaa_profit_per_plane": aaa["profit"] / aaa["vehicles"],
                "opex_engines": dict(opex["engines"]),
                "aaa_engines": dict(aaa["engines"]),
            })
    opex_vehicles = sum(row["opex_vehicles"] for row in observations)
    aaa_vehicles = sum(row["aaa_vehicles"] for row in observations)
    opex_profit = sum(row["opex_profit"] for row in observations)
    aaa_profit = sum(row["aaa_profit"] for row in observations)
    opex_engines = Counter()
    aaa_engines = Counter()
    for row in observations:
        opex_engines.update(row["opex_engines"])
        aaa_engines.update(row["aaa_engines"])
    return {
        "services": len(observations),
        "opex_vehicles": opex_vehicles,
        "aaa_vehicles": aaa_vehicles,
        "opex_profit_last_year_gbp": round(opex_profit, 3),
        "aaa_profit_last_year_gbp": round(aaa_profit, 3),
        "opex_profit_per_plane_gbp": round(opex_profit / opex_vehicles, 3) if opex_vehicles else None,
        "aaa_profit_per_plane_gbp": round(aaa_profit / aaa_vehicles, 3) if aaa_vehicles else None,
        "opex_profit_wins": sum(row["opex_profit"] > row["aaa_profit"] for row in observations),
        "aaa_profit_wins": sum(row["aaa_profit"] > row["opex_profit"] for row in observations),
        "opex_engine_mix": dict(opex_engines.most_common()),
        "aaa_engine_mix": dict(aaa_engines.most_common()),
        "profit_per_plane_ratio_aaa_over_opex": (
            round((aaa_profit / aaa_vehicles) / (opex_profit / opex_vehicles), 6)
            if aaa_vehicles and opex_vehicles and opex_profit != 0 else None
        ),
        "observations": observations,
    }


def summarize(rows):
    latest = {}
    for row in rows:
        seed = row.get("seed")
        if seed not in latest or row.get("date", "") > latest[seed].get("date", ""):
            latest[seed] = row
    return {
        "latest_dates": {str(seed): snap["date"] for seed, snap in sorted(latest.items())},
        "opex": _company_summary(latest, 0),
        "aaahogex": _company_summary(latest, 1),
        "same_market_same_cargo_full_prior_year": _common_market_summary(latest),
        "profit_definition": "VEHS.common.profit_last_year / 256; full prior year requires build_year <= snapshot_year-2",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c98_vs_aaa_engines_5x6.json")
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 10:
        parser.error("--max-workers doit etre entre 1 et 10")

    enable_savegame_cleanup()
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ())
    aaa = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    cfg = make_cfg(1970)
    experiments = [{
        "bench_context": "duel", "bench_arm": "current-default-vs-AAAHogEx",
        "seed": seed, "days": 365 * args.years, "openttd_config": cfg,
        "ais": (opex, aaa),
    } for seed in args.seeds]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.max_workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarize(rows)
    payload = {
        "purpose": "C98 realised AIR profitability and engine mix, current default vs AAAHogEx",
        "years": args.years, "seeds": args.seeds, "rows": rows, "summary": summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
