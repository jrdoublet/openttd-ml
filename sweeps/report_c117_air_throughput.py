#!/usr/bin/env python3
"""Recalcule et imprime le resume compact d'un artefact C117 existant."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from diag_c117_air_throughput import analyse

METRICS = (
    "realized_pax_pm", "realized_base_ratio", "realized_shadow_ratio",
    "realized_pred_carried_ratio", "load_factor", "headway_days",
    "pred_headway_days", "headway_ratio", "fleet_ratio",
    "waiting_mean", "rating_mean", "revenue_ratio", "yield_ratio",
    "operating_profit_ratio", "net_profit_ratio", "mail_pm", "mail_per_pax",
)


def compact(group):
    out = {"n": group.get("n")}
    for key in METRICS:
        stat = group.get(key, {})
        out[key] = {
            "n": stat.get("n"),
            "mean": stat.get("mean"),
            "median": stat.get("median"),
        }
    out["limit_class_counts"] = group.get("limit_class_counts", {})
    out["completed_trips"] = group.get("completed_trips", 0)
    out["unobserved_transitions"] = group.get("unobserved_transitions", 0)
    out["unobserved_transition_rate"] = group.get("unobserved_transition_rate")
    out["short_leg_windows"] = group.get("short_leg_windows", 0)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    analysis = analyse(payload["rows"])
    if args.write:
        payload["analysis"] = analysis
        args.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report = {
        "health": payload.get("health"),
        "event_count": analysis["event_count"],
        "analysis_event_count": analysis["analysis_event_count"],
        "line_count": analysis["line_count"],
        "overall": compact(analysis["overall"]),
        "by_arm": {k: compact(v) for k, v in analysis["by_arm"].items()},
        "by_age": {k: compact(v) for k, v in analysis["by_age"].items()},
        "by_arm_age": {k: compact(v) for k, v in analysis["by_arm_age"].items()},
        "by_capacity_class": {
            k: compact(v) for k, v in analysis["by_capacity_class"].items()
        },
        "ramp": analysis["ramp"],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
