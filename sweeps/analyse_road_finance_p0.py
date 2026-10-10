#!/usr/bin/env python3
"""Read ROAD P0 diagnostic engine logs, distinguishing visits from distinct ODs.

Requires --script-debug during the diagnostic campaign. Absence of lines in
non-debug logs is UNKNOWN, never interpreted as zero exposure.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re


EVENTS = ("ROAD_FINANCE_P0", "ROAD_FINANCE_UNLOCK_P0",
          "ROAD_FINANCE_POSTPLAN_P0", "ROAD_FINANCE_BUILD_P0")
TOKEN = re.compile(r"([a-z][a-z_0-9]*)=([^\s]+)")
RUN = re.compile(r"(.+)_seed(\d+)_r(\d+)\.log$")


def parse_logs(paths):
    by_run = []
    for path in sorted(paths):
        name = RUN.match(path.name)
        if not name:
            continue
        events = defaultdict(list)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            for kind in EVENTS:
                hit = line.find(kind + " ")
                if hit < 0:
                    continue
                row = {}
                for key, value in TOKEN.findall(line[hit + len(kind) + 1:]):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    row[key] = value
                events[kind].append(row)
                break
        gate = events["ROAD_FINANCE_P0"]
        unlocked = events["ROAD_FINANCE_UNLOCK_P0"]
        plans = events["ROAD_FINANCE_POSTPLAN_P0"]
        builds = events["ROAD_FINANCE_BUILD_P0"]
        od_keys = {
            (r.get("src"), r.get("dst"), r.get("kind"), r.get("cargo"))
            for r in unlocked
        }
        dated_od = {
            (r.get("date"), r.get("src"), r.get("dst"), r.get("kind"), r.get("cargo"))
            for r in unlocked
        }
        by_run.append({
            "policy": name.group(1), "seed": int(name.group(2)),
            "repeat": int(name.group(3)),
            "exposure_known": bool(gate),
            "selection_calls_with_road": len(gate),
            "candidate_visits": sum(r.get("observed", 0) for r in gate),
            "candidate_visits_eligible_121": sum(r.get("eligible121", 0) for r in gate),
            "candidate_visits_eligible_100": sum(r.get("eligible100", 0) for r in gate),
            "candidate_visits_unlocked": sum(r.get("unlocked", 0) for r in gate),
            "unlocked_events": len(unlocked),
            "unique_unlocked_od": len(od_keys),
            "unique_unlocked_dated_od": len(dated_od),
            "unlocked_visits_in_top": sum(r.get("in_top", 0) for r in unlocked),
            "postplan_attempts": len(plans),
            "postplan_cash_shortages": sum(r.get("shortage", 0) for r in plans),
            "builds": len(builds),
            "build_successes": sum(r.get("ok", 0) for r in builds),
            "build_actual_at_return": sum(r.get("actual", 0) for r in builds),
            "unknowns": ["counterfactual_build_constructibility",
                         "net_loss_after_delayed_refund", "unique_candidate_visits_outside_unlocked"],
        })
    return {"runs": by_run, "logs": len(by_run),
            "runs_with_observed_road_selection": sum(r["exposure_known"] for r in by_run)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = parse_logs(args.logs.glob("*.log"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"logs": result["logs"], "runs_with_observed_road_selection":
                      result["runs_with_observed_road_selection"],
                      "runs": result["runs"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
