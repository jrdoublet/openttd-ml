#!/usr/bin/env python3
"""C119: quantify payment-distance contribution on a C117-style artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics

import analyse_c119_air_income_shadow as c119


ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    "payment_distance_over_flight",
    "actual_over_legacy", "actual_over_time_only", "actual_over_distance_only",
    "actual_over_distance_time", "actual_over_distance_time_mail",
    "actual_over_mail_full", "actual_over_time_mail_full",
    "actual_over_distance_time_mail_full",
    "actual_over_distance_time_actual_mail",
    "mail_full_per_pred_pax", "actual_mail_per_pax", "pax_load_factor",
    "time_gain", "distance_gain", "distance_time_gain", "distance_time_mail_gain",
    "mail_full_gain", "time_mail_full_gain", "distance_time_mail_full_gain",
)


def stat(values):
    values = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c117", type=Path, default=ROOT / "results/c119_distance_shadow_5x6_20260928.json")
    parser.add_argument("--aggregate", type=Path, default=ROOT / "results/c119_distance_shadow_5x6_20260928_aggregate.json")
    parser.add_argument("--out", type=Path, default=ROOT / "results/c119_distance_decomposition_20260928.json")
    args = parser.parse_args()

    payload = json.loads(args.c117.read_text(encoding="utf-8"))
    aggregate = json.loads(args.aggregate.read_text(encoding="utf-8"))
    static = c119.static_by_line(payload)
    mail_ratio = c119.engine_mail_ratios(payload)
    rows = []
    for row in aggregate["mature_rows"]:
        meta = static.get((row.get("seed"), row.get("line")), {})
        distance = meta.get("distance")
        payment_distance = meta.get("payment_distance")
        engine = meta.get("engine")
        pred = row.get("pred_revenue_per_carried")
        actual = row.get("revenue_per_pax")
        pred_days = row.get("pred_oneway_days")
        if not all(isinstance(v, (int, float)) and v > 0 for v in (distance, payment_distance, pred, pred_days, actual)):
            continue
        if engine not in mail_ratio:
            continue
        speed = c119.script_air_speed(engine)
        if not isinstance(speed, (int, float)) or speed <= 0:
            continue
        legacy_days = max(1, int(math.ceil(float(pred_days))))
        aaa_days = max(1, int(distance + 30) * 664 // int(speed) // 24)
        pax_l = c119.cargo_income(distance, legacy_days, c119.PAX_PAYMENT)
        mail_l = c119.cargo_income(distance, legacy_days, c119.MAIL_PAYMENT)
        pax_a = c119.cargo_income(distance, aaa_days, c119.PAX_PAYMENT)
        mail_a = c119.cargo_income(distance, aaa_days, c119.MAIL_PAYMENT)
        legacy_raw = pax_l + 0.15 * mail_l
        if legacy_raw <= 0:
            continue
        scale = float(pred) / legacy_raw
        time_only = (pax_a + 0.15 * mail_a) * scale
        pax_pd_l = c119.cargo_income(payment_distance, legacy_days, c119.PAX_PAYMENT)
        mail_pd_l = c119.cargo_income(payment_distance, legacy_days, c119.MAIL_PAYMENT)
        pax_pd_a = c119.cargo_income(payment_distance, aaa_days, c119.PAX_PAYMENT)
        mail_pd_a = c119.cargo_income(payment_distance, aaa_days, c119.MAIL_PAYMENT)
        distance_only = (pax_pd_l + 0.15 * mail_pd_l) * scale
        distance_time = (pax_pd_a + 0.15 * mail_pd_a) * scale
        distance_time_mail = (pax_pd_a + mail_ratio[engine] * mail_pd_a) * scale
        pred_n = row.get("live_avg") if False else row.get("fleet_vs_pred")
        pred_n = None
        # Static C117 prediction fields remain available in the aggregate row.
        # fleet_vs_pred is realised/predicted, so use the original raw pred_n
        # reconstructed from headway: pred_headway = 2*pred_oneway/pred_n.
        pred_headway = row.get("pred_headway_days")
        if isinstance(pred_headway, (int, float)) and pred_headway > 0:
            pred_n = 2.0 * float(pred_days) / float(pred_headway)
        pred_carried = row.get("pred_carried")
        build_capacity = row.get("build_capacity")
        mail_full_per_pred_pax = None
        mail_full = time_mail_full = distance_time_mail_full = None
        if all(isinstance(v, (int, float)) and v > 0 for v in (pred_n, pred_carried, build_capacity)):
            engine_mail_capacity = float(build_capacity) * mail_ratio[engine]
            mail_full_pm = float(pred_n) * engine_mail_capacity * 30.4 / float(pred_days)
            mail_full_per_pred_pax = mail_full_pm / float(pred_carried)
            mail_full = (pax_l + mail_full_per_pred_pax * mail_l) * scale
            time_mail_full = (pax_a + mail_full_per_pred_pax * mail_a) * scale
            distance_time_mail_full = (pax_pd_a + mail_full_per_pred_pax * mail_pd_a) * scale
        actual_mail = row.get("mail_per_pax")
        distance_time_actual_mail = None
        if isinstance(actual_mail, (int, float)) and actual_mail >= 0:
            distance_time_actual_mail = (pax_pd_a + float(actual_mail) * mail_pd_a) * scale
        rows.append({
            "seed": row.get("seed"), "line": row.get("line"),
            "payment_distance_over_flight": payment_distance / float(distance),
            "actual_over_legacy": actual / float(pred),
            "actual_over_time_only": actual / time_only,
            "actual_over_distance_only": actual / distance_only,
            "actual_over_distance_time": actual / distance_time,
            "actual_over_distance_time_mail": actual / distance_time_mail,
            "actual_over_mail_full": actual / mail_full if mail_full else None,
            "actual_over_time_mail_full": actual / time_mail_full if time_mail_full else None,
            "actual_over_distance_time_mail_full": actual / distance_time_mail_full if distance_time_mail_full else None,
            "actual_over_distance_time_actual_mail": actual / distance_time_actual_mail if distance_time_actual_mail else None,
            "mail_full_per_pred_pax": mail_full_per_pred_pax,
            "actual_mail_per_pax": row.get("mail_per_pax"),
            "pax_load_factor": row.get("load_factor"),
            "time_gain": time_only / float(pred),
            "distance_gain": distance_only / float(pred),
            "distance_time_gain": distance_time / float(pred),
            "distance_time_mail_gain": distance_time_mail / float(pred),
            "mail_full_gain": mail_full / float(pred) if mail_full else None,
            "time_mail_full_gain": time_mail_full / float(pred) if time_mail_full else None,
            "distance_time_mail_full_gain": distance_time_mail_full / float(pred) if distance_time_mail_full else None,
        })
    result = {"source": str(args.c117), "n": len(rows), "mature": {f: stat([r.get(f) for r in rows]) for f in FIELDS}, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n": result["n"], "mature": result["mature"]}, indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
