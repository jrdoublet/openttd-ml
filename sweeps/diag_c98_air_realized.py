#!/usr/bin/env python3
"""C98 : diagnostic passif du biais AIR predit/realise par moteur et ligne."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

DEFAULT_SEEDS = (42, 100, 999)
TAG_RE = re.compile(r"C98_AIR_REALIZED\s+(.*)")

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def parse_value(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_fields(text: str) -> dict:
    fields = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = parse_value(value)
    return fields


def keep(row):
    seed = row.get("experiment", {}).get("seed")
    events = []
    for fields_s in TAG_RE.findall(row.get("output", "") or ""):
        event = parse_fields(fields_s)
        event["seed"] = seed
        events.append(event)
    if not events:
        return ()
    return ({"seed": seed, "date": str(row.get("date", "")), "events": events},)


def safe_div(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b == 0:
        return None
    return float(a) / float(b)


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def pct(n, d):
    return round(100.0 * n / d, 3) if d else None


def distance_band(distance):
    if not isinstance(distance, (int, float)) or distance < 0:
        return "unknown"
    if distance < 50:
        return "<50"
    if distance < 100:
        return "50-99"
    if distance < 200:
        return "100-199"
    return ">=200"


def station_rating_for_headway(headway_days):
    """Mirror the current default ECONOMY_FIX rating model for offline C98 checks."""
    if not isinstance(headway_days, (int, float)) or headway_days <= 0:
        return None
    if headway_days < 7.5:
        pickup = 130.0
    elif headway_days < 15.0:
        pickup = 95.0
    elif headway_days < 30.0:
        pickup = 50.0
    elif headway_days < 52.5:
        pickup = 25.0
    else:
        pickup = 0.0
    other = 50.0 * 255.0 / 100.0 - 95.0
    return max(0.0, min(100.0, 100.0 * (other + pickup) / 255.0))


def enrich(event):
    e = dict(event)
    pn = e.get("pred_n")
    rn = e.get("real_n")
    pred_p = e.get("pred_p")
    real_p = e.get("real_p")
    pred_r = e.get("pred_r")
    real_r = e.get("real_r")
    pred_amort = e.get("pred_amort")
    pred_pp = safe_div(pred_p, pn)
    real_pp = safe_div(real_p, rn)
    pred_rpp = safe_div(pred_r, pn)
    real_rpp = safe_div(real_r, rn)
    e["pred_profit_per_plane"] = pred_pp
    e["real_profit_per_plane"] = real_pp
    e["profit_per_plane_ratio"] = safe_div(real_pp, pred_pp)
    e["pred_revenue_per_plane"] = pred_rpp
    e["real_revenue_per_plane"] = real_rpp
    e["revenue_per_plane_ratio"] = safe_div(real_rpp, pred_rpp)
    if all(isinstance(v, (int, float)) for v in (real_p, pn, rn, pred_amort)) and rn > 0:
        e["c82_like_real"] = real_p * pn / rn - pred_amort
        e["c82_like_ratio"] = safe_div(e["c82_like_real"], pred_p)
    else:
        e["c82_like_real"] = None
        e["c82_like_ratio"] = None
    ratings = [e.get("rating_a"), e.get("rating_b")]
    ratings = [float(v) for v in ratings if isinstance(v, (int, float)) and v >= 0]
    e["real_rating"] = statistics.mean(ratings) if ratings else None
    e["rating_delta"] = (
        e["real_rating"] - e["pred_rating"]
        if isinstance(e.get("real_rating"), (int, float)) and isinstance(e.get("pred_rating"), (int, float))
        else None
    )
    pax_ratio = safe_div(e.get("pax_load"), e.get("pax_cap"))
    mail_ratio = safe_div(e.get("mail_load"), e.get("mail_cap"))
    moving_ratio = safe_div(e.get("moving"), rn)
    depot_ratio = safe_div(e.get("depot"), rn)
    e["pax_load_pct"] = 100.0 * pax_ratio if pax_ratio is not None else None
    e["mail_load_pct"] = 100.0 * mail_ratio if mail_ratio is not None else None
    e["moving_pct"] = 100.0 * moving_ratio if moving_ratio is not None else None
    e["depot_pct"] = 100.0 * depot_ratio if depot_ratio is not None else None
    speed_avg = safe_div(e.get("speed_sum"), e.get("speed_n"))
    # AIVehicle.GetCurrentSpeed AIR is on the raw vehicle scale whereas
    # AIEngine.GetMaxSpeed is already adjusted by vehicle.plane_speed in NoAI 15.3.
    speed_div = e.get("plane_speed_div")
    speed_api_scale = safe_div(speed_avg, speed_div)
    speed_ratio = safe_div(speed_api_scale, e.get("engine_speed"))
    e["moving_speed_avg"] = speed_avg
    e["moving_speed_api_scale"] = speed_api_scale
    e["moving_speed_pct_max"] = 100.0 * speed_ratio if speed_ratio is not None else None
    mail_cap_ratio = safe_div(e.get("mail_cap"), e.get("pax_cap"))
    e["mail_capacity_pct_pax"] = 100.0 * mail_cap_ratio if mail_cap_ratio is not None else None
    e["distance_band"] = distance_band(e.get("distance"))
    monthly_pax = e.get("monthly_pax")
    pred_capacity = e.get("pred_capacity")
    pred_trips_pm = e.get("pred_trips_pm")
    predicted_monthly_capacity = None
    if all(isinstance(v, (int, float)) for v in (pn, pred_capacity, pred_trips_pm)):
        predicted_monthly_capacity = float(pn) * float(pred_capacity) * float(pred_trips_pm)
    e["pred_monthly_capacity"] = predicted_monthly_capacity
    e["pred_capacity_utilization"] = safe_div(e.get("pred_carried"), predicted_monthly_capacity)
    offered = None
    if isinstance(monthly_pax, (int, float)) and isinstance(e.get("pred_rating"), (int, float)):
        offered = float(monthly_pax) * float(e["pred_rating"]) / 100.0
    e["pred_offered"] = offered
    e["pred_capacity_bound"] = int(
        isinstance(predicted_monthly_capacity, (int, float)) and isinstance(offered, (int, float))
        and predicted_monthly_capacity <= offered + 1.0
    )
    capture_ratio = safe_div(e.get("pred_carried"), monthly_pax)
    e["pred_capture_pct_monthly_pax"] = 100.0 * capture_ratio if capture_ratio is not None else None
    route_counts = [v for v in (e.get("live_routes_a"), e.get("live_routes_b")) if isinstance(v, (int, float))]
    e["live_routes_max"] = max(route_counts) if route_counts else None
    e["shared_station"] = int(any(v > 1 for v in route_counts)) if route_counts else 0
    pax_wait = [v for v in (e.get("pax_wait_a"), e.get("pax_wait_b")) if isinstance(v, (int, float)) and v >= 0]
    mail_wait = [v for v in (e.get("mail_wait_a"), e.get("mail_wait_b")) if isinstance(v, (int, float)) and v >= 0]
    e["pax_wait_mean"] = statistics.mean(pax_wait) if pax_wait else None
    e["mail_wait_mean"] = statistics.mean(mail_wait) if mail_wait else None
    distance = e.get("distance")
    api_speed = e.get("engine_speed")
    if isinstance(distance, (int, float)) and isinstance(api_speed, (int, float)) and api_speed > 0:
        flight_days_api = float(distance) / (0.036 * float(api_speed))
        e["flight_days_api"] = flight_days_api
        for delay, label in ((3.0, "delay3"), (15.0, "delay15")):
            one_way = flight_days_api + delay
            e[f"cf_oneway_{label}"] = one_way
            for n_value, n_label in ((pn, "predn"), (rn, "realn")):
                headway = safe_div(2.0 * one_way, n_value)
                e[f"cf_rating_{label}_{n_label}"] = station_rating_for_headway(headway)
    else:
        e["flight_days_api"] = None
        for label in ("delay3", "delay15"):
            e[f"cf_oneway_{label}"] = None
            e[f"cf_rating_{label}_predn"] = None
            e[f"cf_rating_{label}_realn"] = None
    pred_capacity = e.get("pred_capacity")
    engine_capacity = e.get("engine_capacity")
    e["capacity_consistent"] = int(
        isinstance(pred_capacity, (int, float)) and isinstance(engine_capacity, (int, float))
        and pred_capacity == engine_capacity
    )
    return e


def group_summary(events):
    return {
        "n": len(events),
        "pred_profit_per_plane": stats([e.get("pred_profit_per_plane") for e in events]),
        "real_profit_per_plane": stats([e.get("real_profit_per_plane") for e in events]),
        "profit_per_plane_ratio": stats([e.get("profit_per_plane_ratio") for e in events]),
        "pred_revenue_per_plane": stats([e.get("pred_revenue_per_plane") for e in events]),
        "real_revenue_per_plane": stats([e.get("real_revenue_per_plane") for e in events]),
        "revenue_per_plane_ratio": stats([e.get("revenue_per_plane_ratio") for e in events]),
        "c82_like_ratio": stats([e.get("c82_like_ratio") for e in events]),
        "profit_per_plane_delta": stats([
            e.get("real_profit_per_plane") - e.get("pred_profit_per_plane")
            for e in events
            if isinstance(e.get("real_profit_per_plane"), (int, float))
            and isinstance(e.get("pred_profit_per_plane"), (int, float))
        ]),
        "revenue_per_plane_delta": stats([
            e.get("real_revenue_per_plane") - e.get("pred_revenue_per_plane")
            for e in events
            if isinstance(e.get("real_revenue_per_plane"), (int, float))
            and isinstance(e.get("pred_revenue_per_plane"), (int, float))
        ]),
        "pred_rating": stats([e.get("pred_rating") for e in events]),
        "real_rating": stats([e.get("real_rating") for e in events]),
        "rating_delta": stats([e.get("rating_delta") for e in events]),
        "monthly_pax": stats([e.get("monthly_pax") for e in events]),
        "pred_monthly_capacity": stats([e.get("pred_monthly_capacity") for e in events]),
        "pred_capacity_utilization": stats([e.get("pred_capacity_utilization") for e in events]),
        "pred_capture_pct_monthly_pax": stats([e.get("pred_capture_pct_monthly_pax") for e in events]),
        "pred_capacity_bound_pct": pct(sum(e.get("pred_capacity_bound") == 1 for e in events), len(events)),
        "shared_station_pct": pct(sum(e.get("shared_station") == 1 for e in events), len(events)),
        "live_routes_max": stats([e.get("live_routes_max") for e in events]),
        "pax_wait_mean": stats([e.get("pax_wait_mean") for e in events]),
        "mail_wait_mean": stats([e.get("mail_wait_mean") for e in events]),
        "cf_rating_delay3_predn": stats([e.get("cf_rating_delay3_predn") for e in events]),
        "cf_rating_delay15_predn": stats([e.get("cf_rating_delay15_predn") for e in events]),
        "cf_rating_delay15_realn": stats([e.get("cf_rating_delay15_realn") for e in events]),
        "cf_rating_error_delay3_predn": stats([
            e.get("real_rating") - e.get("cf_rating_delay3_predn")
            for e in events
            if isinstance(e.get("real_rating"), (int, float))
            and isinstance(e.get("cf_rating_delay3_predn"), (int, float))
        ]),
        "cf_rating_error_delay15_predn": stats([
            e.get("real_rating") - e.get("cf_rating_delay15_predn")
            for e in events
            if isinstance(e.get("real_rating"), (int, float))
            and isinstance(e.get("cf_rating_delay15_predn"), (int, float))
        ]),
        "cf_rating_error_delay15_realn": stats([
            e.get("real_rating") - e.get("cf_rating_delay15_realn")
            for e in events
            if isinstance(e.get("real_rating"), (int, float))
            and isinstance(e.get("cf_rating_delay15_realn"), (int, float))
        ]),
        "pax_load_pct_snapshot": stats([e.get("pax_load_pct") for e in events]),
        "mail_load_pct_snapshot": stats([e.get("mail_load_pct") for e in events]),
        "mail_capacity_pct_pax": stats([e.get("mail_capacity_pct_pax") for e in events]),
        "moving_pct_snapshot": stats([e.get("moving_pct") for e in events]),
        "depot_pct_snapshot": stats([e.get("depot_pct") for e in events]),
        "moving_speed_pct_max_snapshot": stats([e.get("moving_speed_pct_max") for e in events]),
        "capacity_consistent_pct": pct(sum(e.get("capacity_consistent") == 1 for e in events), len(events)),
    }


def grouped(events, key_fn):
    buckets = defaultdict(list)
    for event in events:
        buckets[str(key_fn(event))].append(event)
    return {key: group_summary(group) for key, group in sorted(buckets.items())}


def unique_events(rows):
    unique = {}
    for row in rows:
        for raw in row.get("events", []):
            event = enrich(raw)
            key = (event.get("seed"), event.get("profit_year"), event.get("line"))
            unique[key] = event
    return list(unique.values())


def summarize(rows):
    events = unique_events(rows)
    mature = [e for e in events if isinstance(e.get("age"), (int, float)) and e.get("age") >= 2]
    consistent = [e for e in mature if e.get("capacity_consistent") == 1]
    basis = consistent or mature
    by_engine = grouped(basis, lambda e: f"{e.get('engine')}:{e.get('engine_name', 'unknown')}")
    return {
        "events": len(events),
        "mature_events": len(mature),
        "mature_capacity_consistent": len(consistent),
        "analysis_basis": "mature_capacity_consistent" if consistent else "mature",
        "overall": group_summary(basis),
        "by_engine": by_engine,
        "by_distance": grouped(basis, lambda e: e.get("distance_band")),
        "by_fleet_size": grouped(basis, lambda e: e.get("real_n")),
        "by_arm": grouped(basis, lambda e: e.get("arm", "unknown")),
        "by_station_sharing": grouped(basis, lambda e: "shared" if e.get("shared_station") else "isolated"),
        "by_live_routes_max": grouped(basis, lambda e: e.get("live_routes_max")),
        "by_age": grouped(basis, lambda e: e.get("age")),
        "by_pred_limit": grouped(basis, lambda e: "capacity" if e.get("pred_capacity_bound") else "demand_rating"),
        "by_seed": grouped(basis, lambda e: e.get("seed")),
        "engine_counts": {key: value["n"] for key, value in by_engine.items()},
        "cadence_note": (
            "NoAI does not expose annual completed trips per line. pred_trips_pm/pred_days are model values; "
            "moving/load/speed are annual-report snapshots and must not be interpreted as annual cadence."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--c99-air-speed-api-fix", action="store_true",
                        help="active C99 pendant la sonde C98 pour mesurer le biais du modele corrige")
    parser.add_argument("--c100-air-trip-physical", action="store_true",
                        help="active C100 pendant la sonde C98 : vitesse API + manoeuvres aeroport physiques")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_c98_air_realized_3x4.json")
    args = parser.parse_args()
    if args.max_workers < 1 or args.max_workers > 10:
        parser.error("--max-workers doit etre entre 1 et 10")

    enable_savegame_cleanup()
    settings = [("decision_log", 1), ("c98_air_realized_probe", 1)]
    if args.c99_air_speed_api_fix:
        settings.append(("c99_air_speed_api_fix", 1))
    if args.c100_air_trip_physical:
        settings.append(("c100_air_trip_physical", 1))
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", tuple(settings))
    cfg = make_cfg(1970)
    experiments = [
        {
            "bench_context": "solo",
            "bench_arm": "OpexAI[" + ",".join(
                ["decision_log=1", "c98_air_realized_probe=1"]
                + (["c99_air_speed_api_fix=1"] if args.c99_air_speed_api_fix else [])
                + (["c100_air_trip_physical=1"] if args.c100_air_trip_physical else [])
            ) + "]",
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex,),
        }
        for seed in args.seeds
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.max_workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarize(rows)
    payload = {
        "purpose": "C98 passive predicted-versus-realised AIR model diagnostic; not adoption evidence",
        "years": args.years,
        "seeds": args.seeds,
        "settings": {
            "decision_log": 1,
            "c98_air_realized_probe": 1,
            "c99_air_speed_api_fix": int(args.c99_air_speed_api_fix),
            "c100_air_trip_physical": int(args.c100_air_trip_physical),
        },
        "rows": rows,
        "summary": summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
