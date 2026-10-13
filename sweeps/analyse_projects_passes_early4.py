#!/usr/bin/env python3
"""Distribution des sondes projects existantes, sans modification moteur.

Un appel PROJECTS_COST n'est pas nécessairement un passage complet : certains
retours précoces de _tryBuildProjects ne le publient pas. Les familles COST,
SELECTION_LIGHT et SCHED_IDLE sont imbriquées et ne doivent pas s'additionner.
La mesure d'opcodes est une horloge de ticks, pas un compteur d'instructions VM.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, Counter
import json
from pathlib import Path
import re
import statistics

from analyse_opcode_early4 import fields, LINE, DATE, YEARS


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lo, hi = int(index), min(int(index) + 1, len(ordered) - 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo), 2)


def distribution(values):
    return {
        "calls": len(values), "total": sum(values),
        "mean": round(statistics.mean(values), 2) if values else None,
        "median": percentile(values, 0.5), "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def parse_events(lines):
    events = defaultdict(lambda: defaultdict(list))
    for raw in lines:
        match = LINE.search(raw)
        if match is None:
            continue
        match = DATE.match(match.group(1))
        if match is None:
            continue
        year, kind, rest = int(match[1]), match[2], match[3]
        if year not in YEARS:
            continue
        data = fields(rest)
        if kind == "PROJECTS_COST":
            if all(k in data for k in ("build_ops", "regen_ops", "fleet_ops", "built")):
                events[year]["project"].append(data)
        elif kind == "SELECTION_LIGHT" and "ops" in data:
            events[year]["selection"].append(data)
        elif kind == "SCHED_IDLE" and data.get("t") == "projects" and "op" in data:
            events[year]["idle"].append(data)
    return events


def summarize(events):
    result = {}
    for year in YEARS:
        records = events.get(year, {})
        project = records.get("project", [])
        selection = records.get("selection", [])
        idle = records.get("idle", [])
        success = [p for p in project if p["built"] > 0]
        regens = [p for p in project if p["regen_ops"] > 0]
        projects = {
            "records": len(project), "passes_with_build": len(success),
            "built_count": sum(p["built"] for p in project),
            "passes_with_regen": len(regens),
            "cost_all_components_non_exclusive_vs_c39": distribution([
                p["build_ops"] + p["fleet_ops"] + p["regen_ops"] for p in project]),
            "build_ops": distribution([p["build_ops"] for p in project]),
            "fleet_ops": distribution([p["fleet_ops"] for p in project]),
            "regen_ops": distribution([p["regen_ops"] for p in project]),
            "build_pass_build_ops": distribution([p["build_ops"] for p in success]),
            "no_build_pass_build_ops": distribution([p["build_ops"] for p in project if p["built"] == 0]),
            "regen_with_build_ops": distribution([p["regen_ops"] for p in success]),
            "regeneration_kind": dict(sorted(Counter(str(p.get("regen", "unknown")) for p in project).items())),
            "stop_reason": dict(sorted(Counter(str(p.get("stop", "unknown")) for p in project).items())),
        }
        by_path = {}
        for name in sorted(set(str(s.get("path")) for s in selection)):
            rows = [s for s in selection if str(s.get("path")) == name]
            by_path[name] = {"ops": distribution([s["ops"] for s in rows]),
                             "considered": distribution([s.get("considered", 0) for s in rows]),
                             "selected": distribution([s.get("selected", 0) for s in rows])}
        idle_by_reason = {}
        for name in sorted(set(str(s.get("r")) for s in idle)):
            rows = [s for s in idle if str(s.get("r")) == name]
            idle_by_reason[name] = {"ops": distribution([s["op"] for s in rows]),
                                    "progress_flagged": sum(s.get("w") == 1 for s in rows)}
        result[str(year)] = {"projects_cost": projects, "selection": by_path,
                              "scheduler": idle_by_reason,
                              "completeness": {
                                  "project_cost_records": len(project),
                                  "scheduler_project_records": len(idle),
                                  "same_count": len(project) == len(idle),
                              }}
    return result


def run(folder, seeds):
    by_seed = {}
    pooled_events = defaultdict(lambda: defaultdict(list))
    for seed in seeds:
        matches = list(folder.glob(f"*seed{seed}_r0.log"))
        if len(matches) != 1:
            raise ValueError(f"seed={seed}: expected one log, found {len(matches)}")
        with matches[0].open(encoding="utf-8", errors="replace") as stream:
            events = parse_events(stream)
            by_seed[str(seed)] = summarize(events)
            for year, families in events.items():
                for family, rows in families.items():
                    pooled_events[year][family].extend(rows)
    return {"seeds": seeds, "years": list(YEARS), "by_seed": by_seed,
            "pooled_calls": summarize(pooled_events),
            "notes": [
                "Annual time buckets are dates of individual probe emissions; C39 reports are offset to previous accounting year.",
                "PROJECTS_COST build+fleet+regen are disjoint only inside logged _tryBuildProjects passes, not from task, selection, idle or A*.",
                "PROJECTS_COST can miss early returns and pending rail searches; completeness compares its count with SCHED_IDLE.",
                "SCHED_IDLE work=1 is a scheduler outcome, not proof of economic return.",
                "Elapsed tick-based ops include command waiting and cannot be identified as CPU/VM instructions.",
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    args = parser.parse_args()
    result = run(args.logs, args.seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for year in YEARS:
        parts = [result["by_seed"][str(s)][str(year)]["projects_cost"] for s in args.seeds]
        total_cost = statistics.mean(p["cost_all_components_non_exclusive_vs_c39"]["total"] for p in parts)
        built = statistics.mean(p["built_count"] for p in parts)
        pooled = result["pooled_calls"][str(year)]
        cost = pooled["projects_cost"]["cost_all_components_non_exclusive_vs_c39"]
        print(f"{year}: cost_components={total_cost/1e6:.3f}M/seed; "
              f"builds={built:.1f}/seed; cost_pass_calls={cost['calls']}; "
              f"mean={cost['mean']/1000:.1f}k p50={cost['median']/1000:.1f}k "
              f"p95={cost['p95']/1000:.1f}k max={cost['max']/1000:.1f}k")
        for path, fields in pooled["selection"].items():
            ops = fields["ops"]
            print(f"  selection.{path}: calls={ops['calls']} total={ops['total']/1e6:.3f}M "
                  f"p50={ops['median']/1000:.1f}k p95={ops['p95']/1000:.1f}k "
                  f"considered_mean={fields['considered']['mean']}")
        print(f"  built_passes={pooled['projects_cost']['passes_with_build']} "
              f"regen_passes={pooled['projects_cost']['passes_with_regen']} "
              f"stops={pooled['projects_cost']['stop_reason']}")


if __name__ == "__main__":
    main()
