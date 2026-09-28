#!/usr/bin/env python3
"""Analyse C117 : demande -> debit AIR reel -> capacite -> revenu."""

from __future__ import annotations

from collections import defaultdict
import math
import statistics


def safe_div(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b == 0:
        return None
    return float(a) / float(b)


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None, "min": None, "max": None}
    values = sorted(values)

    def percentile(p):
        if len(values) == 1:
            return values[0]
        x = (len(values) - 1) * p
        lo = int(math.floor(x))
        hi = int(math.ceil(x))
        if lo == hi:
            return values[lo]
        return values[lo] * (hi - x) + values[hi] * (x - lo)

    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "p25": round(percentile(0.25), 6),
        "p75": round(percentile(0.75), 6),
        "min": round(values[0], 6),
        "max": round(values[-1], 6),
    }


def age_band(event):
    bucket = event.get("age_bucket")
    if not isinstance(bucket, (int, float)):
        return "unknown"
    bucket = int(bucket)
    if bucket <= 2:
        return "m1-3"
    if bucket <= 5:
        return "m4-6"
    if bucket <= 11:
        return "m7-12"
    return "m>12"


def capacity_class(event):
    cap = event.get("build_capacity")
    if not isinstance(cap, (int, float)) or cap < 0:
        return "unknown"
    if cap <= 50:
        return "<=50"
    if cap <= 100:
        return "51-100"
    return ">100"


def enrich(raw):
    e = dict(raw)
    pax_pm = e.get("pax_pm")
    base = e.get("base_monthly")
    shadow = e.get("shadow_monthly")
    pred_carried = e.get("pred_carried")
    seats_pm = e.get("seats_pm")
    revenue_pm = e.get("revenue_est_pm")
    profit_pm = e.get("profit_pm")
    pred_revenue_y = e.get("pred_revenue_y")
    pred_profit_y = e.get("pred_profit_y")
    pred_running_y = e.get("pred_running_y")
    pred_vehicle_running_y = e.get("pred_vehicle_running_y")
    pred_amort_y = e.get("pred_amort_y")
    pred_n = e.get("pred_n")
    pred_oneway_days = e.get("pred_oneway_days")

    e["age_band"] = age_band(e)
    e["capacity_class"] = capacity_class(e)
    if all(isinstance(v, (int, float)) for v in (pred_n, pred_oneway_days)) and pred_n > 0:
        e["pred_headway_days"] = 2.0 * float(pred_oneway_days) / float(pred_n)
    else:
        e["pred_headway_days"] = None
    e["headway_ratio"] = safe_div(e.get("headway_days"), e["pred_headway_days"])
    e["fleet_ratio"] = safe_div(e.get("live_avg"), pred_n)
    e["realized_base_ratio"] = safe_div(pax_pm, base)
    e["realized_shadow_ratio"] = safe_div(pax_pm, shadow) if isinstance(shadow, (int, float)) and shadow > 0 else None
    e["realized_pred_carried_ratio"] = safe_div(pax_pm, pred_carried)
    e["capacity_utilization"] = safe_div(pax_pm, seats_pm)
    e["pred_revenue_pm"] = float(pred_revenue_y) / 12.0 if isinstance(pred_revenue_y, (int, float)) else None
    e["revenue_ratio"] = safe_div(revenue_pm, e["pred_revenue_pm"])
    e["pred_revenue_per_carried"] = safe_div(e["pred_revenue_pm"], pred_carried)

    if isinstance(pred_vehicle_running_y, (int, float)):
        e["pred_vehicle_operating_profit_pm"] = (
            (float(pred_revenue_y) - float(pred_vehicle_running_y)) / 12.0
            if isinstance(pred_revenue_y, (int, float)) else None
        )
    else:
        e["pred_vehicle_operating_profit_pm"] = None
    e["operating_profit_ratio"] = safe_div(profit_pm, e["pred_vehicle_operating_profit_pm"])

    # Predicted net profit includes airport maintenance + amortisation, while
    # AIVehicle profit does not. Build a model-like realised net by applying the
    # same predicted fixed costs to the actually realised vehicle profit.
    if all(isinstance(v, (int, float)) for v in (
        profit_pm, pred_running_y, pred_vehicle_running_y, pred_amort_y
    )):
        infra_running_pm = (float(pred_running_y) - float(pred_vehicle_running_y)) / 12.0
        amort_pm = float(pred_amort_y) / 12.0
        e["realized_model_like_profit_pm"] = float(profit_pm) - infra_running_pm - amort_pm
    else:
        e["realized_model_like_profit_pm"] = None
    e["pred_net_profit_pm"] = float(pred_profit_y) / 12.0 if isinstance(pred_profit_y, (int, float)) else None
    e["net_profit_ratio"] = safe_div(e["realized_model_like_profit_pm"], e["pred_net_profit_pm"])
    e["revenue_per_pax"] = safe_div(revenue_pm, pax_pm)
    e["yield_ratio"] = safe_div(e["revenue_per_pax"], e["pred_revenue_per_carried"])
    e["mail_per_pax"] = safe_div(e.get("mail_pm"), pax_pm)
    e["profit_per_capital_pm"] = safe_div(profit_pm, e.get("capital"))

    waits = [v for v in (e.get("wait_a"), e.get("wait_b")) if isinstance(v, (int, float)) and v >= 0]
    ratings = [v for v in (e.get("rating_a"), e.get("rating_b")) if isinstance(v, (int, float)) and v >= 0]
    e["waiting_mean"] = statistics.mean(waits) if waits else None
    e["rating_mean"] = statistics.mean(ratings) if ratings else None

    lf = e.get("load_factor")
    waiting = e.get("waiting_mean")
    cap_avg = e.get("cap_avg")
    if isinstance(lf, (int, float)) and lf >= 0.9:
        e["limit_class"] = "capacity_limited"
    elif (
        isinstance(lf, (int, float)) and lf < 0.75
        and isinstance(waiting, (int, float))
        and isinstance(cap_avg, (int, float)) and cap_avg > 0
        and waiting < 0.25 * cap_avg
    ):
        e["limit_class"] = "demand_limited"
    else:
        e["limit_class"] = "mixed_or_uncertain"
    return e


def group_summary(events):
    n = len(events)
    classes = defaultdict(int)
    for e in events:
        classes[e.get("limit_class", "unknown")] += 1
    completed_trips = sum(int(e.get("trips", 0) or 0) for e in events)
    unobserved = sum(int(e.get("unobserved_transitions", 0) or 0) for e in events)
    short_leg_windows = sum(
        1 for e in events
        if isinstance(e.get("leg_days_min"), (int, float))
        and isinstance(e.get("sample_days"), (int, float))
        and e.get("leg_days_min") >= 0
        and e.get("leg_days_min") <= e.get("sample_days")
    )
    return {
        "n": n,
        "realized_pax_pm": stats([e.get("pax_pm") for e in events]),
        "realized_base_ratio": stats([e.get("realized_base_ratio") for e in events]),
        "realized_shadow_ratio": stats([e.get("realized_shadow_ratio") for e in events]),
        "realized_pred_carried_ratio": stats([e.get("realized_pred_carried_ratio") for e in events]),
        "load_factor": stats([
            e.get("load_factor") for e in events
            if isinstance(e.get("load_factor"), (int, float)) and e.get("load_factor") >= 0
        ]),
        "seats_pm": stats([e.get("seats_pm") for e in events]),
        "pax_per_live_plane_pm": stats([
            safe_div(e.get("pax_pm"), e.get("live_avg")) for e in events
        ]),
        "headway_days": stats([
            e.get("headway_days") for e in events
            if isinstance(e.get("headway_days"), (int, float)) and e.get("headway_days") > 0
        ]),
        "pred_headway_days": stats([e.get("pred_headway_days") for e in events]),
        "headway_ratio": stats([
            e.get("headway_ratio") for e in events
            if isinstance(e.get("headway_ratio"), (int, float)) and e.get("headway_ratio") > 0
        ]),
        "fleet_ratio": stats([e.get("fleet_ratio") for e in events]),
        "leg_days_min": stats([e.get("leg_days_min") for e in events if e.get("leg_days_min", -1) >= 0]),
        "leg_days_max": stats([e.get("leg_days_max") for e in events if e.get("leg_days_max", -1) >= 0]),
        "waiting_mean": stats([e.get("waiting_mean") for e in events]),
        "rating_mean": stats([e.get("rating_mean") for e in events]),
        "revenue_ratio": stats([e.get("revenue_ratio") for e in events]),
        "pred_revenue_per_carried": stats([e.get("pred_revenue_per_carried") for e in events]),
        "operating_profit_ratio": stats([e.get("operating_profit_ratio") for e in events]),
        "net_profit_ratio": stats([e.get("net_profit_ratio") for e in events]),
        "revenue_per_pax": stats([e.get("revenue_per_pax") for e in events]),
        "yield_ratio": stats([e.get("yield_ratio") for e in events]),
        "mail_per_pax": stats([e.get("mail_per_pax") for e in events]),
        "profit_per_capital_pm": stats([e.get("profit_per_capital_pm") for e in events]),
        "mail_pm": stats([e.get("mail_pm") for e in events]),
        "invalid_order_samples": sum(int(e.get("invalid_order_samples", 0) or 0) for e in events),
        "completed_trips": completed_trips,
        "unobserved_transitions": unobserved,
        "unobserved_transition_rate": safe_div(unobserved, completed_trips + unobserved),
        "short_leg_windows": short_leg_windows,
        "limit_class_counts": dict(sorted(classes.items())),
    }


def grouped(events, key_fn):
    buckets = defaultdict(list)
    for e in events:
        buckets[str(key_fn(e))].append(e)
    return {k: group_summary(v) for k, v in sorted(buckets.items())}


def ramp_summary(events):
    by_line = defaultdict(list)
    for e in events:
        key = (e.get("seed"), e.get("line"))
        by_line[key].append(e)
    thresholds = (0.50, 0.75, 0.90)
    reached = {t: [] for t in thresholds}
    stable_values = []
    eligible = 0
    for line_events in by_line.values():
        line_events = sorted(
            [e for e in line_events if isinstance(e.get("age_bucket"), (int, float))],
            key=lambda e: int(e["age_bucket"]),
        )
        stable = [
            e.get("pax_pm") for e in line_events
            if int(e["age_bucket"]) >= 6 and isinstance(e.get("pax_pm"), (int, float))
        ]
        if len(stable) < 3:
            continue
        stable_pax = statistics.median(stable)
        if stable_pax <= 0:
            continue
        eligible += 1
        stable_values.append(stable_pax)
        for threshold in thresholds:
            target = stable_pax * threshold
            first = None
            for i in range(len(line_events) - 1):
                a, b = line_events[i], line_events[i + 1]
                if (
                    int(b["age_bucket"]) == int(a["age_bucket"]) + 1
                    and isinstance(a.get("pax_pm"), (int, float))
                    and isinstance(b.get("pax_pm"), (int, float))
                    and a["pax_pm"] >= target and b["pax_pm"] >= target
                ):
                    first = int(a["age_bucket"]) + 1  # human month, bucket 0 => month 1
                    break
            if first is not None:
                reached[threshold].append(first)
    return {
        "eligible_lines": eligible,
        "stable_pax_pm": stats(stable_values),
        "months_to_50pct_stable": stats(reached[0.50]),
        "months_to_75pct_stable": stats(reached[0.75]),
        "months_to_90pct_stable": stats(reached[0.90]),
        "definition": "stable = median pax/month from age bucket >= 6; threshold requires 2 consecutive 30-day windows",
    }


def analyse(rows):
    unique = {}
    for row in rows:
        seed = row.get("seed")
        for raw in row.get("events", []):
            e = enrich(raw)
            e["seed"] = seed
            unique[(seed, e.get("line"), e.get("age_bucket"))] = e
    events = list(unique.values())

    # Exclude very short/incomplete windows from ratio summaries, but keep them
    # in raw_events for audit.
    basis = [
        e for e in events
        if isinstance(e.get("period_days"), (int, float)) and e["period_days"] >= 20
    ]
    return {
        "event_count": len(events),
        "analysis_event_count": len(basis),
        "line_count": len({(e.get("seed"), e.get("line")) for e in basis}),
        "overall": group_summary(basis),
        "by_arm": grouped(basis, lambda e: e.get("arm", "unknown")),
        "by_age": grouped(basis, lambda e: e.get("age_band", "unknown")),
        "by_engine": grouped(basis, lambda e: e.get("engine", "unknown")),
        "by_capacity_class": grouped(basis, lambda e: e.get("capacity_class", "unknown")),
        "by_arm_age": grouped(basis, lambda e: f"{e.get('arm', 'unknown')}|{e.get('age_band', 'unknown')}"),
        "ramp": ramp_summary(basis),
        "measurement": {
            "pax": "sum of maximum passenger cargo observed while each aircraft is VS_RUNNING on a completed A<->B leg",
            "units": "passengers per observed completed leg, normalized to passengers per 30.4 days as pax_pm",
            "capacity": "sum of passenger seats on the same completed legs; load_factor = pax / seat_legs",
            "revenue": "vehicle profit delta + prorated AIVehicle.GetRunningCost; includes passenger + aircraft mail revenue",
            "profit": "AIVehicle profit delta is vehicle operating profit; realized_model_like_profit subtracts predicted infra running + amortisation for comparison with model net profit",
            "cadence": "order-index transitions sampled every 2 game days; manual depot orders excluded",
            "deduplication": "checkpoint logs are cumulative; retain one final event per (seed,line,age_bucket)",
        },
        "raw_events": events,
    }
