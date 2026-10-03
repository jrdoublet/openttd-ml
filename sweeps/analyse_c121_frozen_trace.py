#!/usr/bin/env python3
"""Compact reader for the first post-success AIR autopsy snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def first(events, kind):
    return next((event for event in events if event.get("kind") == kind), None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    print("health", payload.get("health"))
    for row in payload.get("rows", []):
        events = row.get("autopsy") or []
        passed = first(events, "PASS") or {}
        built = first(events, "BUILD_SNAPSHOT") or {}
        seq = built.get("seq")
        candidates = [e for e in events if e.get("kind") == "POST_CAND" and e.get("seq") == seq]
        selected = next((e for e in candidates if e.get("rank") == built.get("rank")), None) or {}
        print(
            "ROW", row.get("seed"), row.get("policy_id"),
            "build", f"{built.get('y')}-{built.get('m'):02d}-{built.get('d'):02d}" if built else None,
            "tick", built.get("tick"), "rank", built.get("rank"),
            "built_before", passed.get("built_before"), "kpass", passed.get("k_pass"),
            "kpass_active", passed.get("k_pass_active"),
            "cash_after", built.get("cash_after"), "available_after", built.get("available_after"),
        )
        print(
            " SELECT", selected.get("mode"), selected.get("arm"),
            "towns", selected.get("town_a"), selected.get("town_b"),
            "dist", selected.get("distance"), "monthly_pax", selected.get("monthly_pax"),
            "profit", selected.get("profit"), "revenue", selected.get("revenue"),
            "finance", selected.get("finance"), "score", selected.get("fund_score"),
            "early_bonus", selected.get("early_bonus"),
            "econ_profit", selected.get("econ_profit"), "econ_planes", selected.get("econ_planes"),
            "decision_profit", selected.get("decision_profit"),
            "decision_planes", selected.get("decision_planes"),
            "target_planes", selected.get("target_planes"),
        )
        print(" TOP", [(e.get("rank"), e.get("mode"), e.get("arm"), e.get("town_a"), e.get("town_b"), e.get("profit"), e.get("finance"), round(float(e.get("fund_score") or 0), 1)) for e in candidates[:8]])
        perf = row.get("air_plan_perf") or []
        if perf:
            print(" PERF_FIRST", perf[0])
        builds = row.get("c121_builds") or []
        if builds:
            first_build = builds[0]
            keys = (
                "line", "arm", "pax_a", "pax_b", "mail_a", "mail_b", "target_n",
                "target_profit", "decision_kdec", "decision_n", "decision_profit",
                "decision_capital", "actual_n", "actual_profit", "actual_revenue",
                "plane_price", "airport_capital", "new_airports", "payment_distance",
            )
            print(" C121_BUILD", {key: first_build.get(key) for key in keys})
        trace = row.get("air_build_trace") or []
        failed = [line for line in trace if "failed" in line]
        attempts = [line for line in trace if "Start Build AirRoute" in line]
        print(" BUILD_TRACE", "attempts", len(attempts), "failures", len(failed))
        for line in (attempts[:3] + failed[:6]):
            print("   ", line)


if __name__ == "__main__":
    main()
