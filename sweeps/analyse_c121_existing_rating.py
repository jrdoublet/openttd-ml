#!/usr/bin/env python3
"""C121 : teste le rating courant des hubs comme observation, sans changer l'AI."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from analyse_c117_aggregate import aggregate

def ratio(actual, predicted):
    if not isinstance(actual, (int, float)) or not isinstance(predicted, (int, float)) or predicted <= 0:
        return None
    return float(actual) / float(predicted)

def stats(values):
    vals = sorted(float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v)))
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    def q(frac):
        pos = (len(vals) - 1) * frac
        lo, hi = int(math.floor(pos)), int(math.ceil(pos))
        return vals[lo] if lo == hi else vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
    return {"n": len(vals), "mean": statistics.fmean(vals), "median": statistics.median(vals),
            "p25": q(0.25), "p75": q(0.75)}

def choose_rating(build, current_key, model_key):
    current = build.get(current_key)
    if isinstance(current, (int, float)) and current >= 0:
        return float(current), "current"
    model = build.get(model_key)
    return (float(model), "model") if isinstance(model, (int, float)) else (None, "missing")

def analyse(payload):
    builds, mature = {}, defaultdict(list)
    for run in payload.get("rows", []):
        seed = run.get("seed")
        for build in run.get("c121_builds", []):
            line = build.get("line")
            if isinstance(seed, int) and isinstance(line, (int, float)):
                builds[(seed, int(line))] = build
        for event in run.get("events", []):
            line, age = event.get("line"), event.get("age_bucket")
            if isinstance(seed, int) and isinstance(line, (int, float)) and isinstance(age, (int, float)) and age >= 6:
                mature[(seed, int(line))].append(event)

    rows = []
    for key, events in sorted(mature.items()):
        build = builds.get(key)
        if build is None:
            continue
        observed = aggregate(events)
        rp_a, src_pa = choose_rating(build, "current_pax_rating_a", "rating_pax_a")
        rp_b, src_pb = choose_rating(build, "current_pax_rating_b", "rating_pax_b")
        rm_a, src_ma = choose_rating(build, "current_mail_rating_a", "rating_mail_a")
        rm_b, src_mb = choose_rating(build, "current_mail_rating_b", "rating_mail_b")
        hybrid_rating_pct = None if rp_a is None or rp_b is None else (rp_a + rp_b) * 50.0 / 255.0
        hybrid_pax = hybrid_mail = hybrid_revenue = None
        required = ("pax_a", "pax_b", "mail_a", "mail_b", "pax_dir_capacity", "mail_dir_capacity",
                    "pax_income", "mail_income")
        if all(isinstance(build.get(k), (int, float)) for k in required) and None not in (rp_a, rp_b, rm_a, rm_b):
            pax_cap, mail_cap = float(build["pax_dir_capacity"]), float(build["mail_dir_capacity"])
            hybrid_pax = min(float(build["pax_a"]) * rp_a / 255.0, pax_cap) + min(
                float(build["pax_b"]) * rp_b / 255.0, pax_cap)
            hybrid_mail = min(float(build["mail_a"]) * rm_a / 255.0, mail_cap) + min(
                float(build["mail_b"]) * rm_b / 255.0, mail_cap)
            hybrid_revenue = 12.0 * (
                hybrid_pax * float(build["pax_income"]) + hybrid_mail * float(build["mail_income"]))
        actual_total = observed.get("pax_pm", 0.0) + observed.get("mail_pm", 0.0)
        model_total = build.get("actual_pax", 0) + build.get("actual_mail", 0)
        hybrid_total = None if hybrid_pax is None or hybrid_mail is None else hybrid_pax + hybrid_mail
        actual_revenue_y = observed.get("revenue_pm", 0.0) * 12.0
        rows.append({
            "seed": key[0], "line": key[1], "arm": build.get("arm"),
            "rating_source_pax_a": src_pa, "rating_source_pax_b": src_pb,
            "rating_source_mail_a": src_ma, "rating_source_mail_b": src_mb,
            "model_rating_pct": build.get("rating"), "hybrid_rating_pct": hybrid_rating_pct,
            "actual_rating_pct": observed.get("rating_mean"),
            "actual_over_model_rating": ratio(observed.get("rating_mean"), build.get("rating")),
            "actual_over_hybrid_rating": ratio(observed.get("rating_mean"), hybrid_rating_pct),
            "model_total_pm": model_total, "hybrid_total_pm": hybrid_total, "actual_total_pm": actual_total,
            "actual_over_model_total": ratio(actual_total, model_total),
            "actual_over_hybrid_total": ratio(actual_total, hybrid_total),
            "model_revenue_y": build.get("actual_revenue"), "hybrid_revenue_y": hybrid_revenue,
            "actual_revenue_y": actual_revenue_y,
            "actual_over_model_revenue": ratio(actual_revenue_y, build.get("actual_revenue")),
            "actual_over_hybrid_revenue": ratio(actual_revenue_y, hybrid_revenue),
        })
    metrics = ("actual_over_model_rating", "actual_over_hybrid_rating",
               "actual_over_model_total", "actual_over_hybrid_total",
               "actual_over_model_revenue", "actual_over_hybrid_revenue")
    by_arm = {}
    for arm in sorted({r["arm"] for r in rows if r.get("arm") is not None}):
        group = [r for r in rows if r.get("arm") == arm]
        by_arm[arm] = {"line_count": len(group), **{m: stats([r.get(m) for r in group]) for m in metrics}}
    return {"source_campaign": payload.get("campaign_id"), "matched_mature_lines": len(rows),
            "overall": {m: stats([r.get(m) for r in rows]) for m in metrics},
            "by_arm": by_arm, "rows": rows}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = analyse(json.loads(args.input.read_text(encoding="utf-8")))
    out = args.out or args.input.with_name(args.input.stem + "_existing_rating.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    print(f"Sortie: {out}")

if __name__ == "__main__":
    main()
