#!/usr/bin/env python3
"""Print a compact C98 model-decomposition view from a diagnostic JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


KEEP = (
    "n", "profit_per_plane_ratio", "revenue_per_plane_ratio",
    "pred_rating", "real_rating", "rating_delta", "monthly_pax",
    "pred_monthly_capacity", "pred_capacity_utilization",
    "pred_capture_pct_monthly_pax", "pred_capacity_bound_pct",
    "shared_station_pct", "live_routes_max", "pax_wait_mean", "mail_wait_mean",
    "pax_load_pct_snapshot", "mail_load_pct_snapshot",
)


def compact(group):
    return {key: group.get(key) for key in KEEP if key in group}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    summary = json.loads(args.path.read_text(encoding="utf-8"))["summary"]
    out = {"overall": compact(summary["overall"])}
    for section in ("by_arm", "by_station_sharing", "by_live_routes_max", "by_age", "by_pred_limit", "by_engine"):
        out[section] = {key: compact(group) for key, group in summary.get(section, {}).items()}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
