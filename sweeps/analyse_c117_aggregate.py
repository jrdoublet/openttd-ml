#!/usr/bin/env python3
"""C117 : agrégation anti-aliasing des fenêtres 30 jours par ligne et âge."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics


def div(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b == 0:
        return None
    return float(a) / float(b)


def stat(values):
    values = sorted(
        float(v) for v in values
        if isinstance(v, (int, float)) and math.isfinite(float(v))
    )
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}

    def pct(p):
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
        "p25": round(pct(0.25), 6),
        "p75": round(pct(0.75), 6),
    }


def weighted(group, field):
    num = 0.0
    den = 0.0
    for e in group:
        value = e.get(field)
        days = e.get("period_days")
        if (
            not isinstance(value, (int, float))
            or not isinstance(days, (int, float))
            or value < 0 or days <= 0
        ):
            continue
        num += float(value) * float(days)
        den += float(days)
    return num / den if den > 0 else None


def static_value(group, field):
    vals = [
        e.get(field) for e in group
        if isinstance(e.get(field), (int, float))
    ]
    return statistics.median(vals) if vals else None


def model_rating(headway_days):
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


def aggregate(group):
    group = sorted(group, key=lambda e: int(e.get("age_bucket", 0) or 0))
    first = group[0]
    days = sum(
        float(e.get("period_days", 0) or 0)
        for e in group
        if isinstance(e.get("period_days"), (int, float)) and e.get("period_days", 0) > 0
    )
    if days <= 0:
        return None

    def total(field):
        return sum(
            float(e.get(field, 0) or 0)
            for e in group
            if isinstance(e.get(field, 0), (int, float))
        )

    pax = total("pax")
    seats = total("seat_legs")
    mail = total("mail")
    mail_seats = total("mail_seat_legs")
    profit = total("profit")
    running = total("run_est")
    trips = total("trips")
    missed = total("unobserved_transitions")
    leg_days_sum = total("leg_days_sum")
    leg_days_n = total("leg_days_n")

    pax_pm = pax * 30.4 / days
    seats_pm = seats * 30.4 / days
    mail_pm = mail * 30.4 / days
    profit_pm = profit * 30.4 / days
    run_pm = running * 30.4 / days
    revenue_pm = profit_pm + run_pm

    base = static_value(group, "base_monthly")
    shadow = static_value(group, "shadow_monthly")
    pred_carried = static_value(group, "pred_carried")
    pred_revenue_y = static_value(group, "pred_revenue_y")
    pred_profit_y = static_value(group, "pred_profit_y")
    pred_running_y = static_value(group, "pred_running_y")
    pred_vehicle_running_y = static_value(group, "pred_vehicle_running_y")
    pred_amort_y = static_value(group, "pred_amort_y")
    pred_n = static_value(group, "pred_n")
    pred_oneway_days = static_value(group, "pred_oneway_days")
    capital = static_value(group, "capital")
    build_capacity = static_value(group, "build_capacity")

    pred_revenue_pm = pred_revenue_y / 12.0 if pred_revenue_y is not None else None
    pred_vehicle_profit_pm = (
        (pred_revenue_y - pred_vehicle_running_y) / 12.0
        if pred_revenue_y is not None and pred_vehicle_running_y is not None else None
    )
    realized_model_like_profit_pm = None
    pred_net_profit_pm = pred_profit_y / 12.0 if pred_profit_y is not None else None
    if (
        pred_running_y is not None
        and pred_vehicle_running_y is not None
        and pred_amort_y is not None
    ):
        realized_model_like_profit_pm = (
            profit_pm
            - (pred_running_y - pred_vehicle_running_y) / 12.0
            - pred_amort_y / 12.0
        )

    wait_a = weighted(group, "wait_a")
    wait_b = weighted(group, "wait_b")
    rating_a = weighted(group, "rating_a")
    rating_b = weighted(group, "rating_b")
    waits = [v for v in (wait_a, wait_b) if isinstance(v, (int, float))]
    ratings = [v for v in (rating_a, rating_b) if isinstance(v, (int, float))]
    waiting_mean = statistics.mean(waits) if waits else None
    rating_mean = statistics.mean(ratings) if ratings else None
    live_avg = weighted(group, "live_avg")
    cap_avg = weighted(group, "cap_avg")
    load_factor = div(pax, seats)
    headway_days = 2.0 * days / trips if trips > 0 else None
    actual_leg_days = div(leg_days_sum, leg_days_n)
    pred_headway_days = (
        2.0 * pred_oneway_days / pred_n
        if isinstance(pred_oneway_days, (int, float))
        and isinstance(pred_n, (int, float)) and pred_n > 0 else None
    )
    pred_seats_pm = (
        pred_n * build_capacity * 30.4 / pred_oneway_days
        if isinstance(pred_oneway_days, (int, float)) and pred_oneway_days > 0
        and isinstance(pred_n, (int, float))
        and isinstance(build_capacity, (int, float)) else None
    )
    pred_rating = model_rating(pred_headway_days)

    if isinstance(load_factor, (int, float)) and load_factor >= 0.9:
        limit_class = "capacity_limited"
    elif (
        isinstance(load_factor, (int, float)) and load_factor < 0.75
        and isinstance(waiting_mean, (int, float))
        and isinstance(cap_avg, (int, float)) and cap_avg > 0
        and waiting_mean < 0.25 * cap_avg
    ):
        limit_class = "demand_limited"
    else:
        limit_class = "mixed_or_uncertain"

    revenue_per_pax = div(revenue_pm, pax_pm)
    pred_revenue_per_carried = div(pred_revenue_pm, pred_carried)
    return {
        "seed": first.get("seed"),
        "line": first.get("line"),
        "arm": first.get("arm", "unknown"),
        "age_band": first.get("age_band", "unknown"),
        "first_age_bucket": first.get("age_bucket"),
        "last_age_bucket": group[-1].get("age_bucket"),
        "build_engine": first.get("build_engine"),
        "build_capacity": build_capacity,
        "capacity_class": first.get("capacity_class", "unknown"),
        "period_days": days,
        "pax": pax,
        "pax_pm": pax_pm,
        "seats_pm": seats_pm,
        "load_factor": load_factor,
        "mail_pm": mail_pm,
        "mail_per_pax": div(mail_pm, pax_pm),
        "base_monthly": base,
        "shadow_monthly": shadow,
        "pred_carried": pred_carried,
        "realized_base_ratio": div(pax_pm, base),
        "realized_shadow_ratio": div(pax_pm, shadow),
        "realized_pred_carried_ratio": div(pax_pm, pred_carried),
        "actual_leg_days": actual_leg_days,
        "pred_oneway_days": pred_oneway_days,
        "leg_time_ratio": div(actual_leg_days, pred_oneway_days),
        "headway_days": headway_days,
        "pred_headway_days": pred_headway_days,
        "headway_ratio": div(headway_days, pred_headway_days),
        "pred_seats_pm": pred_seats_pm,
        "seat_throughput_ratio": div(seats_pm, pred_seats_pm),
        "trips": trips,
        "unobserved_transitions": missed,
        "transition_capture_ratio": div(trips, trips + missed),
        "waiting_mean": waiting_mean,
        "rating_mean": rating_mean,
        "pred_rating": pred_rating,
        "rating_ratio": div(rating_mean, pred_rating),
        "live_avg": live_avg,
        "fleet_vs_pred": div(live_avg, pred_n),
        "cap_avg": cap_avg,
        "profit_pm": profit_pm,
        "revenue_pm": revenue_pm,
        "pred_revenue_pm": pred_revenue_pm,
        "revenue_ratio": div(revenue_pm, pred_revenue_pm),
        "revenue_per_pax": revenue_per_pax,
        "pred_revenue_per_carried": pred_revenue_per_carried,
        "yield_ratio": div(revenue_per_pax, pred_revenue_per_carried),
        "pred_vehicle_profit_pm": pred_vehicle_profit_pm,
        "operating_profit_ratio": div(profit_pm, pred_vehicle_profit_pm),
        "realized_model_like_profit_pm": realized_model_like_profit_pm,
        "pred_net_profit_pm": pred_net_profit_pm,
        "net_profit_ratio": div(realized_model_like_profit_pm, pred_net_profit_pm),
        "profit_per_capital_pm": div(profit_pm, capital),
        "limit_class": limit_class,
    }


def aggregate_by(events, key_fn):
    groups = defaultdict(list)
    for e in events:
        groups[key_fn(e)].append(e)
    result = []
    for group in groups.values():
        row = aggregate(group)
        if row is not None:
            result.append(row)
    return result


def summary(rows):
    classes = Counter(r.get("limit_class", "unknown") for r in rows)
    trips = sum(float(r.get("trips", 0) or 0) for r in rows)
    missed = sum(float(r.get("unobserved_transitions", 0) or 0) for r in rows)
    return {
        "n": len(rows),
        "pax_pm": stat([r.get("pax_pm") for r in rows]),
        "realized_base_ratio": stat([r.get("realized_base_ratio") for r in rows]),
        "realized_shadow_ratio": stat([r.get("realized_shadow_ratio") for r in rows]),
        "realized_pred_carried_ratio": stat([r.get("realized_pred_carried_ratio") for r in rows]),
        "load_factor": stat([r.get("load_factor") for r in rows]),
        "actual_leg_days": stat([r.get("actual_leg_days") for r in rows]),
        "pred_oneway_days": stat([r.get("pred_oneway_days") for r in rows]),
        "leg_time_ratio": stat([r.get("leg_time_ratio") for r in rows]),
        "headway_days": stat([r.get("headway_days") for r in rows]),
        "pred_headway_days": stat([r.get("pred_headway_days") for r in rows]),
        "headway_ratio": stat([r.get("headway_ratio") for r in rows]),
        "seat_throughput_ratio": stat([r.get("seat_throughput_ratio") for r in rows]),
        "waiting_mean": stat([r.get("waiting_mean") for r in rows]),
        "rating_mean": stat([r.get("rating_mean") for r in rows]),
        "pred_rating": stat([r.get("pred_rating") for r in rows]),
        "rating_ratio": stat([r.get("rating_ratio") for r in rows]),
        "live_avg": stat([r.get("live_avg") for r in rows]),
        "fleet_vs_pred": stat([r.get("fleet_vs_pred") for r in rows]),
        "revenue_ratio": stat([r.get("revenue_ratio") for r in rows]),
        "yield_ratio": stat([r.get("yield_ratio") for r in rows]),
        "mail_per_pax": stat([r.get("mail_per_pax") for r in rows]),
        "pred_revenue_per_carried": stat([r.get("pred_revenue_per_carried") for r in rows]),
        "operating_profit_ratio": stat([r.get("operating_profit_ratio") for r in rows]),
        "net_profit_ratio": stat([r.get("net_profit_ratio") for r in rows]),
        "revenue_per_pax": stat([r.get("revenue_per_pax") for r in rows]),
        "profit_per_capital_pm": stat([r.get("profit_per_capital_pm") for r in rows]),
        "transition_capture_ratio": div(trips, trips + missed),
        "limit_class_counts": dict(sorted(classes.items())),
    }


def grouped_summary(rows, key_fn):
    groups = defaultdict(list)
    for row in rows:
        groups[str(key_fn(row))].append(row)
    return {key: summary(group) for key, group in sorted(groups.items())}


def network_weighted(events):
    pax = 0.0
    seats = 0.0
    base_exposure = 0.0
    shadow_exposure = 0.0
    pred_exposure = 0.0
    for e in events:
        days = e.get("period_days")
        if not isinstance(days, (int, float)) or days <= 0:
            continue
        days = float(days)
        pax += float(e.get("pax", 0) or 0)
        seats += float(e.get("seat_legs", 0) or 0)
        base = e.get("base_monthly")
        shadow = e.get("shadow_monthly")
        pred = e.get("pred_carried")
        if isinstance(base, (int, float)) and base > 0:
            base_exposure += float(base) * days / 30.4
        if isinstance(shadow, (int, float)) and shadow > 0:
            shadow_exposure += float(shadow) * days / 30.4
        if isinstance(pred, (int, float)) and pred > 0:
            pred_exposure += float(pred) * days / 30.4
    return {
        "realized_base_ratio": div(pax, base_exposure),
        "realized_shadow_ratio": div(pax, shadow_exposure),
        "realized_pred_carried_ratio": div(pax, pred_exposure),
        "load_factor": div(pax, seats),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    raw = payload["analysis"]["raw_events"]
    basis = [
        e for e in raw
        if isinstance(e.get("period_days"), (int, float)) and e.get("period_days") >= 20
    ]
    line_band = aggregate_by(
        basis, lambda e: (e.get("seed"), e.get("line"), e.get("age_band"))
    )
    lifetime = aggregate_by(
        basis, lambda e: (e.get("seed"), e.get("line"))
    )
    mature_events = [
        e for e in basis
        if isinstance(e.get("age_bucket"), (int, float)) and int(e.get("age_bucket")) >= 6
    ]
    mature = aggregate_by(
        mature_events, lambda e: (e.get("seed"), e.get("line"))
    )
    result = {
        "source": str(args.input),
        "method": (
            "Aggregate raw 30-day C117 windows before ratios. line_band = one row per "
            "(seed,line,age band); lifetime = one row per line; mature = age bucket >=6."
        ),
        "network_weighted": network_weighted(basis),
        "lifetime": summary(lifetime),
        "mature": summary(mature),
        "by_arm_lifetime": grouped_summary(lifetime, lambda r: r.get("arm", "unknown")),
        "by_arm_mature": grouped_summary(mature, lambda r: r.get("arm", "unknown")),
        "by_age": grouped_summary(line_band, lambda r: r.get("age_band", "unknown")),
        "by_arm_age": grouped_summary(
            line_band, lambda r: f"{r.get('arm', 'unknown')}|{r.get('age_band', 'unknown')}"
        ),
        "by_build_engine_mature": grouped_summary(
            mature, lambda r: r.get("build_engine", "unknown")
        ),
        "by_capacity_class_mature": grouped_summary(
            mature, lambda r: r.get("capacity_class", "unknown")
        ),
        "ramp": payload["analysis"]["ramp"],
        "counts": {
            "raw_events": len(raw),
            "basis_events": len(basis),
            "line_band_rows": len(line_band),
            "lifetime_lines": len(lifetime),
            "mature_lines": len(mature),
        },
        "line_band_rows": line_band,
        "lifetime_rows": lifetime,
        "mature_rows": mature,
    }
    out = args.out or args.input.with_name(args.input.stem + "_aggregate.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    compact = {k: result[k] for k in (
        "counts", "network_weighted", "lifetime", "mature",
        "by_arm_lifetime", "by_arm_mature", "by_age", "ramp",
    )}
    print(json.dumps(compact, indent=2))
    print(f"Sortie: {out}")


if __name__ == "__main__":
    main()
