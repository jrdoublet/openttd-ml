#!/usr/bin/env python3
"""C119: decompose C117 AIR yield error into payment-time and engine-mail shadows."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]

PAX_PAYMENT = (3185, 0, 24)
MAIL_PAYMENT = (4550, 20, 90)
AIRCRAFT_ENGINE_BASE = 215
AIRCRAFT_OLD_SPEED = [
    37, 37, 74, 181, 37, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74,
    74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 181, 74, 181, 37,
    37, 74, 74, 181, 25, 40, 25,
]


def script_air_speed(engine_id):
    idx = int(engine_id) - AIRCRAFT_ENGINE_BASE
    if idx < 0 or idx >= len(AIRCRAFT_OLD_SPEED):
        return None
    display_speed = (AIRCRAFT_OLD_SPEED[idx] * 128) // 10
    return display_speed // 4


def cargo_income(distance, days, spec):
    initial_payment, periods1, periods2 = spec
    transit = max(0, int(days) * 2 // 5)
    over1 = max(transit - periods1, 0)
    over2 = max(over1 - periods2, 0)
    min_factor, max_factor, frac = 31, 255, 16
    over_max = min_factor - max_factor
    if periods2 > -over_max:
        over_max += transit - periods1
    else:
        over_max += 2 * (transit - periods1) - periods2
    if over_max > 0:
        time_factor = max(2 * min_factor * frac * frac // (over_max + 2 * frac), 1)
        return int(distance) * time_factor * initial_payment >> 25
    time_factor = max(max_factor - over1 - over2, min_factor)
    return int(distance) * time_factor * initial_payment >> 21


def div(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b == 0:
        return None
    return float(a) / float(b)


def stat(values):
    values = sorted(float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v)))
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    def pct(p):
        if len(values) == 1:
            return values[0]
        x = (len(values) - 1) * p
        lo, hi = int(math.floor(x)), int(math.ceil(x))
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


def engine_mail_ratios(c117):
    totals = defaultdict(lambda: [0.0, 0.0])
    for row in c117.get("rows", []):
        for e in row.get("events", []):
            engine = e.get("engine")
            seats = e.get("seat_legs")
            mail_seats = e.get("mail_seat_legs")
            if not isinstance(engine, int) or engine < 0:
                continue
            if not isinstance(seats, (int, float)) or seats <= 0:
                continue
            if not isinstance(mail_seats, (int, float)) or mail_seats < 0:
                continue
            if int(e.get("mixed_engine_samples", 0) or 0) != 0:
                continue
            totals[engine][0] += float(mail_seats)
            totals[engine][1] += float(seats)
    return {engine: mail / pax for engine, (mail, pax) in totals.items() if pax > 0}


def static_by_line(c117):
    out = {}
    for row in c117.get("rows", []):
        seed = row.get("seed")
        for e in row.get("events", []):
            line = e.get("line")
            if isinstance(seed, int) and isinstance(line, int):
                out[(seed, line)] = {
                    "distance": e.get("distance"),
                    "payment_distance": e.get("payment_distance"),
                    "engine": e.get("build_engine"),
                    "base_monthly": e.get("base_monthly"),
                    "airport_span_a": e.get("airport_span_a"),
                    "airport_span_b": e.get("airport_span_b"),
                }
    return out


def enrich(rows, static, mail_ratio, legacy_mail_ratio):
    result = []
    for src in rows:
        row = dict(src)
        seed, line = row.get("seed"), row.get("line")
        meta = static.get((seed, line), {})
        engine = meta.get("engine")
        actual = row.get("revenue_per_pax")
        legacy_pred = row.get("pred_revenue_per_carried")
        distance = meta.get("distance")
        payment_distance = meta.get("payment_distance")
        speed = script_air_speed(engine) if isinstance(engine, int) else None
        pred_days = row.get("pred_oneway_days")
        if (not isinstance(engine, int) or engine not in mail_ratio
                or not isinstance(distance, (int, float)) or distance <= 0
                or not isinstance(speed, (int, float)) or speed <= 0
                or not isinstance(pred_days, (int, float)) or pred_days <= 0):
            continue
        legacy_days = max(1, int(math.ceil(float(pred_days))))
        aaa_days = max(1, int(distance + 30) * 664 // int(speed) // 24)
        pax_l = float(cargo_income(distance, legacy_days, PAX_PAYMENT))
        mail_l = float(cargo_income(distance, legacy_days, MAIL_PAYMENT))
        pax_a = float(cargo_income(distance, aaa_days, PAX_PAYMENT))
        mail_a = float(cargo_income(distance, aaa_days, MAIL_PAYMENT))
        engine_mail = float(mail_ratio[engine])
        probe_legacy = pax_l + mail_l * legacy_mail_ratio
        if probe_legacy <= 0 or not isinstance(legacy_pred, (int, float)) or legacy_pred <= 0:
            continue
        scale = float(legacy_pred) / probe_legacy
        fare_time = (pax_a + mail_a * legacy_mail_ratio) * scale
        fare_mail = (pax_l + mail_l * engine_mail) * scale
        fare_both = (pax_a + mail_a * engine_mail) * scale
        fare_distance = fare_distance_time = fare_distance_time_mail = None
        fare_mail_full = fare_time_mail_full = fare_distance_time_mail_full = None
        if isinstance(payment_distance, (int, float)) and payment_distance > 0:
            pax_pd_l = float(cargo_income(payment_distance, legacy_days, PAX_PAYMENT))
            mail_pd_l = float(cargo_income(payment_distance, legacy_days, MAIL_PAYMENT))
            pax_pd_a = float(cargo_income(payment_distance, aaa_days, PAX_PAYMENT))
            mail_pd_a = float(cargo_income(payment_distance, aaa_days, MAIL_PAYMENT))
            fare_distance = (pax_pd_l + mail_pd_l * legacy_mail_ratio) * scale
            fare_distance_time = (pax_pd_a + mail_pd_a * legacy_mail_ratio) * scale
            fare_distance_time_mail = (pax_pd_a + mail_pd_a * engine_mail) * scale
            pred_headway = row.get("pred_headway_days")
            build_capacity = row.get("build_capacity")
            pred_carried = row.get("pred_carried")
            if all(isinstance(v, (int, float)) and v > 0
                   for v in (pred_headway, build_capacity, pred_carried)):
                pred_n = 2.0 * float(pred_days) / float(pred_headway)
                mail_units_pm = (pred_n * float(build_capacity) * engine_mail
                                 * 30.4 / float(pred_days))
                fare_mail_full = scale * (
                    float(pred_carried) * pax_l + mail_units_pm * mail_l
                ) / float(pred_carried)
                fare_time_mail_full = scale * (
                    float(pred_carried) * pax_a + mail_units_pm * mail_a
                ) / float(pred_carried)
                fare_distance_time_mail_full = scale * (
                    float(pred_carried) * pax_pd_a + mail_units_pm * mail_pd_a
                ) / float(pred_carried)
        actual_mail = row.get("mail_per_pax")
        fare_legacy_actual_mail = None
        fare_aaa_actual_mail = None
        fare_actual_physics_raw = None
        actual_days = None
        if isinstance(actual_mail, (int, float)) and actual_mail >= 0:
            fare_legacy_actual_mail = (pax_l + mail_l * float(actual_mail)) * scale
            fare_aaa_actual_mail = (pax_a + mail_a * float(actual_mail)) * scale
            actual_leg = row.get("actual_leg_days")
            if isinstance(actual_leg, (int, float)) and actual_leg > 0:
                actual_days = max(1, int(math.ceil(float(actual_leg))))
                fare_actual_physics_raw = cargo_income(distance, actual_days, PAX_PAYMENT) + float(actual_mail) * cargo_income(distance, actual_days, MAIL_PAYMENT)
        row.update({
            "distance": meta.get("distance"),
            "payment_distance": payment_distance,
            "engine": engine,
            "legacy_days": legacy_days,
            "aaa_days": aaa_days,
            "engine_speed": speed,
            "engine_mail_per_pax_capacity": engine_mail,
            "legacy_probe_scale": scale,
            "fare_legacy": float(legacy_pred),
            "fare_time_only": fare_time,
            "fare_mail_only": fare_mail,
            "fare_time_mail": fare_both,
            "fare_distance_only": fare_distance,
            "fare_distance_time": fare_distance_time,
            "fare_distance_time_mail": fare_distance_time_mail,
            "fare_mail_full": fare_mail_full,
            "fare_time_mail_full": fare_time_mail_full,
            "fare_distance_time_mail_full": fare_distance_time_mail_full,
            "actual_over_legacy": div(actual, legacy_pred),
            "actual_over_time_only": div(actual, fare_time),
            "actual_over_mail_only": div(actual, fare_mail),
            "actual_over_time_mail": div(actual, fare_both),
            "time_gain_vs_legacy": div(fare_time, legacy_pred),
            "mail_gain_vs_legacy": div(fare_mail, legacy_pred),
            "combined_gain_vs_legacy": div(fare_both, legacy_pred),
            "payment_distance_over_flight_distance": div(payment_distance, distance),
            "distance_gain_vs_legacy": div(fare_distance, legacy_pred),
            "distance_time_gain_vs_legacy": div(fare_distance_time, legacy_pred),
            "mail_full_gain_vs_legacy": div(fare_mail_full, legacy_pred),
            "time_mail_full_gain_vs_legacy": div(fare_time_mail_full, legacy_pred),
            "distance_time_mail_full_gain_vs_legacy": div(fare_distance_time_mail_full, legacy_pred),
            "actual_over_distance_only": div(actual, fare_distance),
            "actual_over_distance_time": div(actual, fare_distance_time),
            "actual_over_distance_time_mail": div(actual, fare_distance_time_mail),
            "actual_over_mail_full": div(actual, fare_mail_full),
            "actual_over_time_mail_full": div(actual, fare_time_mail_full),
            "actual_over_distance_time_mail_full": div(actual, fare_distance_time_mail_full),
            "mail_load_gain_vs_legacy": div(fare_legacy_actual_mail, legacy_pred),
            "actual_over_legacy_actual_mail": div(actual, fare_legacy_actual_mail),
            "actual_over_aaa_actual_mail": div(actual, fare_aaa_actual_mail),
            "actual_over_actual_time_actual_mail_raw": div(actual, fare_actual_physics_raw),
            "actual_over_aaa_days": div(row.get("actual_leg_days"), aaa_days),
            "aaa_days_over_actual": div(aaa_days, row.get("actual_leg_days")),
            "actual_over_legacy_days": div(row.get("actual_leg_days"), row.get("pred_oneway_days")),
        })
        pred_carried = row.get("pred_carried")
        revenue_pm = row.get("revenue_pm")
        if isinstance(pred_carried, (int, float)) and pred_carried > 0 and isinstance(revenue_pm, (int, float)):
            row["revenue_actual_over_legacy"] = div(revenue_pm, pred_carried * legacy_pred)
            row["revenue_actual_over_time_only"] = div(revenue_pm, pred_carried * fare_time)
            row["revenue_actual_over_mail_only"] = div(revenue_pm, pred_carried * fare_mail)
            row["revenue_actual_over_time_mail"] = div(revenue_pm, pred_carried * fare_both)
            row["revenue_actual_over_distance_only"] = (
                div(revenue_pm, pred_carried * fare_distance)
                if isinstance(fare_distance, (int, float)) else None
            )
            row["revenue_actual_over_distance_time"] = (
                div(revenue_pm, pred_carried * fare_distance_time)
                if isinstance(fare_distance_time, (int, float)) else None
            )
            row["revenue_actual_over_mail_full"] = (
                div(revenue_pm, pred_carried * fare_mail_full)
                if isinstance(fare_mail_full, (int, float)) else None
            )
            row["revenue_actual_over_time_mail_full"] = (
                div(revenue_pm, pred_carried * fare_time_mail_full)
                if isinstance(fare_time_mail_full, (int, float)) else None
            )
            row["revenue_actual_over_distance_time_mail_full"] = (
                div(revenue_pm, pred_carried * fare_distance_time_mail_full)
                if isinstance(fare_distance_time_mail_full, (int, float)) else None
            )
        spans = [v for v in (meta.get("airport_span_a"), meta.get("airport_span_b"))
                 if isinstance(v, (int, float)) and v > 0]
        row["airport_span"] = max(spans) if spans else None
        row["headway_over_airport_span"] = div(row.get("headway_days"), row.get("airport_span"))
        result.append(row)
    return result


def summary(rows):
    fields = (
        "actual_over_legacy", "actual_over_time_only", "actual_over_mail_only", "actual_over_time_mail",
        "time_gain_vs_legacy", "mail_gain_vs_legacy", "combined_gain_vs_legacy",
        "payment_distance_over_flight_distance", "distance_gain_vs_legacy",
        "distance_time_gain_vs_legacy", "mail_full_gain_vs_legacy",
        "time_mail_full_gain_vs_legacy", "distance_time_mail_full_gain_vs_legacy",
        "actual_over_distance_only", "actual_over_distance_time", "actual_over_distance_time_mail",
        "actual_over_mail_full", "actual_over_time_mail_full", "actual_over_distance_time_mail_full",
        "legacy_probe_scale",
        "mail_load_gain_vs_legacy", "actual_over_legacy_actual_mail",
        "actual_over_aaa_actual_mail", "actual_over_actual_time_actual_mail_raw",
        "actual_over_legacy_days", "actual_over_aaa_days", "aaa_days_over_actual",
        "engine_mail_per_pax_capacity", "mail_per_pax",
        "revenue_actual_over_legacy", "revenue_actual_over_time_only",
        "revenue_actual_over_mail_only", "revenue_actual_over_time_mail",
        "revenue_actual_over_distance_only", "revenue_actual_over_distance_time",
        "revenue_actual_over_mail_full", "revenue_actual_over_time_mail_full",
        "revenue_actual_over_distance_time_mail_full", "headway_over_airport_span",
    )
    return {field: stat([r.get(field) for r in rows]) for field in fields}


def aaa_rated_production(rows, rich_bonus=False):
    ratios = []
    vs_pred = []
    actual_vs_rated = []
    for row in rows:
        speed = row.get("engine_speed")
        production = row.get("base_monthly")
        pred = row.get("pred_carried")
        if not all(isinstance(v, (int, float)) for v in (speed, production, pred)) or production <= 0:
            continue
        station_rate = 170 + max((min(255, int(speed)) - 85) // 4, 0) + (26 if rich_bonus else 0)
        station_rate = min(255, station_rate)
        rated = float(production) * station_rate / 255.0
        ratios.append(div(rated, production))
        vs_pred.append(div(rated, pred))
        actual_vs_rated.append(div(row.get("pax_pm"), rated))
    return {
        "rated_over_input_production": stat(ratios),
        "rated_over_opex_pred_carried": stat(vs_pred),
        "actual_pax_over_rated_base_monthly": stat(actual_vs_rated),
        "note": "Diagnostic only: C117 base_monthly is not AAAHogEx GetExpectedProduction. Applying AAAHogEx stationRate to it does not establish an equivalent production model; maxRouteCapacity cannot be reconstructed because C117 does not log airport type.",
    }


def direction_balance(c117):
    totals = defaultdict(lambda: [0.0, 0.0])
    for row in c117.get("rows", []):
        seed = row.get("seed")
        for e in row.get("events", []):
            line = e.get("line")
            age = e.get("age_bucket")
            period = e.get("period_days")
            if not isinstance(seed, int) or not isinstance(line, int):
                continue
            if not isinstance(age, (int, float)) or age < 6:
                continue
            if not isinstance(period, (int, float)) or period < 20:
                continue
            a, b = e.get("trips_a"), e.get("trips_b")
            if isinstance(a, (int, float)) and a >= 0:
                totals[(seed, line)][0] += float(a)
            if isinstance(b, (int, float)) and b >= 0:
                totals[(seed, line)][1] += float(b)
    balances = []
    for a, b in totals.values():
        if max(a, b) > 0:
            balances.append(min(a, b) / max(a, b))
    return stat(balances)


def mature_load_factors(c117):
    totals = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for row in c117.get("rows", []):
        seed = row.get("seed")
        for e in row.get("events", []):
            line = e.get("line")
            age = e.get("age_bucket")
            period = e.get("period_days")
            if not isinstance(seed, int) or not isinstance(line, int):
                continue
            if not isinstance(age, (int, float)) or age < 6:
                continue
            if not isinstance(period, (int, float)) or period < 20:
                continue
            fields = (e.get("pax"), e.get("seat_legs"), e.get("mail"), e.get("mail_seat_legs"))
            if all(isinstance(v, (int, float)) and v >= 0 for v in fields):
                bucket = totals[(seed, line)]
                for i, value in enumerate(fields):
                    bucket[i] += float(value)
    pax_load, mail_load = [], []
    for pax, seats, mail, mail_seats in totals.values():
        if seats > 0:
            pax_load.append(pax / seats)
        if mail_seats > 0:
            mail_load.append(mail / mail_seats)
    return {
        "pax_load_factor": stat(pax_load),
        "mail_load_factor": stat(mail_load),
    }


def mature_directional_load_factors(c117):
    totals = defaultdict(lambda: [0.0] * 8)
    for row in c117.get("rows", []):
        seed = row.get("seed")
        for e in row.get("events", []):
            line = e.get("line")
            age = e.get("age_bucket")
            period = e.get("period_days")
            if not isinstance(seed, int) or not isinstance(line, int):
                continue
            if not isinstance(age, (int, float)) or age < 6:
                continue
            if not isinstance(period, (int, float)) or period < 20:
                continue
            fields = (
                e.get("pax_a"), e.get("seats_a"), e.get("mail_a"), e.get("mail_seats_a"),
                e.get("pax_b"), e.get("seats_b"), e.get("mail_b"), e.get("mail_seats_b"),
            )
            if all(isinstance(v, (int, float)) and v >= 0 for v in fields):
                bucket = totals[(seed, line)]
                for i, value in enumerate(fields):
                    bucket[i] += float(value)
    pax_a, pax_b, mail_a, mail_b, pax_balance = [], [], [], [], []
    eligible = 0
    both_pax_90 = 0
    for pa, sa, ma, msa, pb, sb, mb, msb in totals.values():
        if sa <= 0 or sb <= 0:
            continue
        eligible += 1
        la, lb = pa / sa, pb / sb
        pax_a.append(la)
        pax_b.append(lb)
        if max(la, lb) > 0:
            pax_balance.append(min(la, lb) / max(la, lb))
        if la >= 0.90 and lb >= 0.90:
            both_pax_90 += 1
        if msa > 0:
            mail_a.append(ma / msa)
        if msb > 0:
            mail_b.append(mb / msb)
    return {
        "eligible_lines": eligible,
        "pax_load_a": stat(pax_a),
        "pax_load_b": stat(pax_b),
        "pax_direction_balance": stat(pax_balance),
        "mail_load_a": stat(mail_a),
        "mail_load_b": stat(mail_b),
        "both_pax_directions_ge_90pct": both_pax_90,
        "both_pax_directions_ge_90pct_ratio": div(both_pax_90, eligible),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c117", type=Path, default=ROOT / "results" / "c117_air_throughput_5x6_20260927_r2.json")
    parser.add_argument("--aggregate", type=Path, default=ROOT / "results" / "c117_air_throughput_5x6_20260927_r2_aggregate.json")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "c119_air_income_shadow_20260928.json")
    parser.add_argument("--legacy-mail-ratio", type=float, default=0.15)
    args = parser.parse_args()

    c117 = json.loads(args.c117.read_text(encoding="utf-8"))
    agg = json.loads(args.aggregate.read_text(encoding="utf-8"))
    static = static_by_line(c117)
    mail_ratio = engine_mail_ratios(c117)
    lifetime = enrich(agg["lifetime_rows"], static, mail_ratio, args.legacy_mail_ratio)
    mature = enrich(agg["mature_rows"], static, mail_ratio, args.legacy_mail_ratio)
    result = {
        "sources": {"c117": str(args.c117), "aggregate": str(args.aggregate)},
        "payment_model": "OpenTTD 15.3 ScriptCargo::GetCargoIncome + GetTransportedGoodsIncome; base cargo specs for this OpenGFX shadow",
        "legacy_mail_ratio": args.legacy_mail_ratio,
        "engine_mail_capacity_ratio": {str(k): v for k, v in sorted(mail_ratio.items())},
        "counts": {"lifetime": len(lifetime), "mature": len(mature)},
        "lifetime": summary(lifetime),
        "mature": summary(mature),
        "aaa_rated_production_nonrich_mature": aaa_rated_production(mature, False),
        "aaa_rated_production_rich_mature": aaa_rated_production(mature, True),
        "direction_trip_balance": direction_balance(c117),
        "mature_load_factors": mature_load_factors(c117),
        "mature_directional_load_factors": mature_directional_load_factors(c117),
        "limitations": [
            "Older C117 artifacts do not split passenger load by direction; the C119 descriptive rerun adds pax_a/pax_b and capacities so bidirectional fullness can be tested directly.",
            "The C119 descriptive rerun logs base stationDateSpan per endpoint, but route-sharing multipliers are still not logged; capacity comparison remains diagnostic.",
            "The engine-mail shadow uses actual AIVehicle capacities observed by C117, not the realised 0.344 mail/passenger load ratio.",
        ],
        "mature_rows": mature,
        "lifetime_rows": lifetime,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    compact = {k: result[k] for k in (
        "counts",
        "mature",
        "aaa_rated_production_nonrich_mature",
        "aaa_rated_production_rich_mature",
        "direction_trip_balance",
        "mature_load_factors",
        "mature_directional_load_factors",
        "limitations",
    )}
    summary_out = args.out.with_name(args.out.stem + "_summary.json")
    summary_out.write_text(json.dumps(compact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(compact, indent=2))
    print(f"Sortie: {args.out}")
    print(f"Synthese: {summary_out}")


if __name__ == "__main__":
    main()
