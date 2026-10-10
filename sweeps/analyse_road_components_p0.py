#!/usr/bin/env python3
"""Compare ROAD B0 command-tariff proxy with real phase costs from engine logs.

Only a completed build with its planned fleet delivered is comparable.
Failed/rolled-back transactions remain separate; they are NOT net losses.
Requires diagnostic engine logs captured with --script-debug.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

# Standalone invocation from repository root and `python -m` both work.
RUN = re.compile(r"(.+)_seed(\d+)_r(\d+)\.log$")
TOKEN = re.compile(r"([a-z][a-z_0-9]*)=([^\s]+)")

TAG = "ROAD_COMPONENTS_P0 "
PHASES = ("trace", "stops", "depot", "vehicles")


def _numbers(rows):
    successes = [r for r in rows if r.get("ok") == 1]
    comparable = [r for r in successes if r.get("comparable") == 1
                  and all(r.get("real_" + p, -1) >= 0 for p in PHASES)
                  and sum(r["real_" + p] for p in PHASES) == r.get("actual")]
    out = {"attempts": len(rows), "successes": len(successes),
           "successes_comparable": len(comparable),
           "successes_incomparable": len(successes) - len(comparable),
           "failures_at_return": len(rows) - len(successes)}
    if not comparable:
        out["comparison_known"] = False
        return out
    actual = sum(r["actual"] for r in comparable)
    post = sum(r["post"] for r in comparable)
    physical = sum(r["components"] for r in comparable)
    out.update({
        "comparison_known": True,
        "actual_success_total": actual,
        "post_model_total": post,
        "component_proxy_total": physical,
        "ratio_actual_to_post": actual / post if post > 0 else None,
        "ratio_actual_to_components": actual / physical if physical > 0 else None,
        "post_mean_absolute_error": sum(abs(r["actual"] - r["post"])
                                        for r in comparable) / len(comparable),
        "component_mean_absolute_error": sum(abs(r["actual"] - r["components"])
                                             for r in comparable) / len(comparable),
        "quote_helper_opcodes_measured": sum(r.get("quote_ops", 0) for r in comparable)
                                         if all("quote_ops" in r for r in comparable) else None,
        "per_phase": {
            p: {"quoted": sum(r["quote_" + p] for r in comparable),
                "observed": sum(r["real_" + p] for r in comparable)}
            for p in PHASES
        },
        "comparable_samples": [{
            "date": r.get("date"), "src": r.get("src"), "dst": r.get("dst"),
            "kind": r.get("kind"), "drive": r.get("drive"),
            "edges": r.get("edges"), "stopstubs": r.get("stopstubs"),
            "depotstub": r.get("depotstub"), "pre": r.get("pre"),
            "post": r["post"], "components": r["components"],
            "actual": r["actual"],
            "quote_ops": r.get("quote_ops"),
            "phase_residuals": {p: r["real_" + p] - r["quote_" + p]
                                for p in PHASES},
        } for r in comparable],
    })
    return out


def analyze_logs(paths):
    runs = []
    all_probe_rows = []
    for path in sorted(paths):
        match = RUN.match(path.name)
        if match is None:
            continue
        rows = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            pos = line.find(TAG)
            if pos < 0:
                continue
            row = {}
            for k, v in TOKEN.findall(line[pos + len(TAG):]):
                try:
                    row[k] = int(v)
                except ValueError:
                    row[k] = v
            rows.append(row)
        all_probe_rows.extend(rows)
        groups = defaultdict(list)
        for row in rows:
            key = "kind=" + str(row.get("kind", "unknown")) + ":drive=" + str(row.get("drive", "unknown"))
            groups[key].append(row)
        runs.append({
            "policy": match.group(1), "seed": int(match.group(2)),
            "repeat": int(match.group(3)), "probe_present": len(rows) > 0,
            "all": _numbers(rows),
            "by_kind_and_drive": {k: _numbers(v) for k, v in sorted(groups.items())},
        })
    return {
        "logs": len(runs), "runs_with_probe_events": sum(r["probe_present"] for r in runs),
        "runs": runs,
        "all_probe_events": _numbers(all_probe_rows),
        "limitations": ["catalog_tariff_per_missing_edge_is_not_exact_command_cost",
                        "simulation_impact_on_scheduler_timing_not_measured",
                        "not_a_counterfactual_cash_or_build_gate",
                        "failures_not_final_net_losses"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    data = analyze_logs(args.logs.glob("*.log"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "logs": data["logs"], "runs_with_probe_events": data["runs_with_probe_events"],
        "all_probe_events": {k: v for k, v in data["all_probe_events"].items()
                             if k != "comparable_samples"},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
