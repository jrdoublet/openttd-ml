#!/usr/bin/env python3
"""Compare le shadow C121 aux observations C117 par age de ligne."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
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


def median(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    return statistics.median(values) if values else None


def weighted(events, field, weight_field="leg_days_n"):
    pairs = [
        (float(event[field]), float(event.get(weight_field, 0)))
        for event in events
        if isinstance(event.get(field), (int, float))
        and event.get(field) >= 0
        and isinstance(event.get(weight_field), (int, float))
        and event.get(weight_field) > 0
    ]
    den = sum(weight for _, weight in pairs)
    return sum(value * weight for value, weight in pairs) / den if den > 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    builds = {}
    events = defaultdict(list)
    for row in payload.get("rows", []):
        seed = row.get("seed")
        for build in row.get("c121_builds", []):
            if isinstance(seed, int) and isinstance(build.get("line"), (int, float)):
                builds[(seed, int(build["line"]))] = build
        for event in row.get("events", []):
            if isinstance(seed, int) and isinstance(event.get("line"), (int, float)):
                events[(seed, int(event["line"]))].append(event)

    windows = (("months_1_3", 0, 2), ("months_4_6", 3, 5), ("months_7_plus", 6, None))
    result = {}
    for name, lo, hi in windows:
        rows = []
        for key, group in events.items():
            build = builds.get(key)
            if build is None:
                continue
            selected = [
                e for e in group
                if isinstance(e.get("age_bucket"), (int, float))
                and e["age_bucket"] >= lo and (hi is None or e["age_bucket"] <= hi)
            ]
            if not selected:
                continue
            obs = aggregate(selected)
            adapted_oneway = weighted(selected, "c121_adapted_oneway_days")
            pred_total = build.get("actual_pax", 0) + build.get("actual_mail", 0)
            actual_total = obs.get("pax_pm", 0.0) + obs.get("mail_pm", 0.0)
            rows.append({
                "arm": build.get("arm"),
                "total": ratio(actual_total, pred_total),
                "leg": ratio(obs.get("actual_leg_days"), build.get("one_way_days")),
                "leg_adapted_live": ratio(obs.get("actual_leg_days"), adapted_oneway),
                "headway": ratio(obs.get("headway_days"), build.get("headway_days")),
                "rating": ratio(obs.get("rating_mean"), build.get("rating")),
                "fleet": ratio(obs.get("live_avg"), build.get("actual_n")),
                "revenue": ratio(obs.get("revenue_pm", 0.0) * 12.0, build.get("actual_revenue")),
                "load_factor": obs.get("load_factor"),
                "pred_pax_capacity_use": ratio(
                    build.get("actual_pax"),
                    2.0 * build.get("pax_dir_capacity", 0)
                ),
                "pred_mail_capacity_use": ratio(
                    build.get("actual_mail"),
                    2.0 * build.get("mail_dir_capacity", 0)
                ),
            })
        result[name] = {}
        for arm in ("ALL", "newpair", "hubsite", "hubhub"):
            arm_rows = rows if arm == "ALL" else [r for r in rows if r.get("arm") == arm]
            result[name][arm] = {
                "n": len(arm_rows),
                **{metric: median([r.get(metric) for r in arm_rows])
                   for metric in (
                       "total", "leg", "leg_adapted_live", "headway", "rating", "fleet", "revenue",
                       "load_factor", "pred_pax_capacity_use", "pred_mail_capacity_use"
                   )},
            }
    out = args.out or args.input.with_name(args.input.stem + "_age_windows.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Sortie: {out}")


if __name__ == "__main__":
    main()
