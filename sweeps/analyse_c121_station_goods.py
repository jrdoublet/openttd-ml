#!/usr/bin/env python3
"""Resume la telemetrie station.goods host-only d'un artefact C121."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def _quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * fraction
    lo = int(pos)
    hi = min(len(ordered) - 1, lo + 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _stats(values):
    values = [float(value) for value in values if isinstance(value, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p25": _quantile(values, 0.25),
        "p75": _quantile(values, 0.75),
    }


def analyse(payload):
    cargo = defaultdict(list)
    capacity_by_cargo = defaultdict(list)
    line_count = 0
    unresolved = 0

    for row in payload.get("rows") or []:
        telemetry = row.get("line_telemetry") or {}
        unresolved += len(telemetry.get("unresolved_vehicles") or [])
        for line in telemetry.get("lines") or []:
            if line.get("mode") != "air":
                continue
            line_count += 1
            for cargo_id, capacity in (line.get("capacity_by_cargo") or {}).items():
                if isinstance(capacity, (int, float)):
                    capacity_by_cargo[str(cargo_id)].append(capacity)
            for endpoint in line.get("endpoint_cargo_stats") or []:
                for cargo_id, good in (endpoint.get("cargo") or {}).items():
                    if isinstance(good, dict):
                        cargo[str(cargo_id)].append(good)

    cargo_summary = {}
    for cargo_id, goods in sorted(cargo.items(), key=lambda item: item[0]):
        rated = [good for good in goods if good.get("rated") and isinstance(good.get("rating"), (int, float))]
        pickup = [good.get("time_since_pickup") for good in goods]
        waiting = [good.get("max_waiting_cargo") for good in goods]
        numeric_waiting = [float(value) for value in waiting if isinstance(value, (int, float))]
        cargo_summary[cargo_id] = {
            "endpoint_observations": len(goods),
            "rated_count": len(rated),
            "unrated_count": len(goods) - len(rated),
            "rating": _stats([good.get("rating") for good in rated]),
            "time_since_pickup": _stats(pickup),
            "never_picked_count": sum(
                isinstance(value, (int, float)) and value >= 255 for value in pickup
            ),
            "max_waiting_cargo": _stats(waiting),
            "waiting_threshold_counts": {
                "gt_100": sum(value > 100 for value in numeric_waiting),
                "gt_300": sum(value > 300 for value in numeric_waiting),
                "gt_600": sum(value > 600 for value in numeric_waiting),
                "gt_1000": sum(value > 1000 for value in numeric_waiting),
                "gt_1500": sum(value > 1500 for value in numeric_waiting),
            },
            "capacity": _stats(capacity_by_cargo.get(cargo_id, [])),
        }

    return {
        "campaign_id": payload.get("campaign_id"),
        "telemetry_air_lines": line_count,
        "unresolved_vehicles": unresolved,
        "cargo": cargo_summary,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyse(payload)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
