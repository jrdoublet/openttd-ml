#!/usr/bin/env python3
"""C121 : isole le biais cargo mature par arm et croissance des endpoints.

Entrée : résumé produit par ``analyse_c121_air_economics_shadow.py``.
Le but est de distinguer :
- erreur du modèle au build ;
- concurrence AIR ajoutée après le build ;
- cadence/service final de la ligne ;
- partage FIFO/capacité.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics


METRICS = (
    "actual_over_pred_pax",
    "actual_over_pred_mail",
    "actual_over_pred_total",
    "actual_over_pred_revenue",
    "actual_over_pred_profit",
    "actual_over_pred_rating",
    "actual_over_live_adapted_leg_days",
    "actual_over_capacity_share_total",
    "actual_over_capacity_share_revenue",
    "actual_over_manual_fifo_fixed_total",
    "actual_over_manual_fifo_fixed_revenue",
    "actual_over_mature_competition_no_slot_fixed_total",
    "actual_over_mature_competition_no_slot_fixed_revenue",
    "actual_over_mature_competition_fixed_pax",
    "actual_over_mature_competition_fixed_mail",
    "actual_over_mature_competition_fixed_total",
    "actual_over_mature_competition_fixed_revenue",
    "actual_over_mature_competition_fifo_fixed_total",
    "actual_over_mature_competition_fifo_fixed_revenue",
    "actual_over_mature_current_service_fixed_total",
    "actual_over_mature_current_service_fixed_revenue",
    "actual_over_mature_current_service_fifo_fixed_total",
    "actual_over_mature_current_service_fifo_fixed_revenue",
)

STRUCTURAL = (
    "route_div_a", "route_div_b", "final_degree_a", "final_degree_b",
    "route_growth_a", "route_growth_b", "route_growth_max",
)


def stats(values):
    vals = sorted(
        float(v) for v in values
        if isinstance(v, (int, float)) and math.isfinite(float(v))
    )
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}

    def q(frac):
        pos = (len(vals) - 1) * frac
        lo, hi = int(math.floor(pos)), int(math.ceil(pos))
        if lo == hi:
            return vals[lo]
        return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)

    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "p25": q(0.25),
        "p75": q(0.75),
    }


def summarize(rows):
    return {
        "line_count": len(rows),
        "limit_class_counts": dict(sorted(Counter(
            str(row.get("limit_class", "unknown")) for row in rows
        ).items())),
        "metrics": {
            metric: stats(row.get(metric) for row in rows)
            for metric in METRICS
        },
        "structure": {
            field: stats(row.get(field) for row in rows)
            for field in STRUCTURAL
        },
    }


def analyse(payload):
    rows = payload.get("rows") or []
    groups = defaultdict(list)
    for row in rows:
        arm = str(row.get("arm", "unknown"))
        growth = str(row.get("route_growth_bucket", "unknown"))
        groups[f"{arm}:{growth}"].append(row)

    return {
        "source_campaign": payload.get("source_campaign"),
        "matched_mature_lines": len(rows),
        "by_arm_growth": {
            key: summarize(group)
            for key, group in sorted(groups.items())
        },
        "growth_2plus_by_arm": {
            arm: summarize([r for r in rows if r.get("arm") == arm and r.get("route_growth_bucket") == "2+"])
            for arm in sorted({r.get("arm") for r in rows if r.get("arm") is not None})
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyse(payload)
    out = args.out or args.input.with_name(args.input.stem + "_growth_bias.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Sortie: {out}")


if __name__ == "__main__":
    main()
