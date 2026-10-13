#!/usr/bin/env python3
"""Attribution séquentielle des resélections aux passages air_fleet.

Cette attribution à la prochaine terminaison SCHED_IDLE ne prouve pas
l'exclusivité en présence d'une réentrance éventuelle; les écarts/ambiguïtés
sont publiés. Tous les opcodes sont des unités de fenêtre tick/OpexOps.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from analyse_opcode_early4 import LINE, DATE, YEARS, fields


def parse(stream):
    data = defaultdict(lambda: defaultdict(lambda: {
        "calls": 0, "task_window_ops": 0, "reselect_calls": 0,
        "reselect_ops": 0,
        "oversized_attributions": 0,
    }))
    pending = []
    unassigned = 0
    for line in stream:
        match = LINE.search(line)
        if not match:
            continue
        date = DATE.match(match[1])
        if not date:
            continue
        year, name, rest = int(date[1]), date[2], date[3]
        if year not in YEARS:
            continue
        row = fields(rest)
        if name == "SELECTION_LIGHT" and row.get("path") == "reselect":
            pending.append((year, row.get("ops", 0)))
        elif name == "SCHED_IDLE":
            task = str(row.get("t", "unknown"))
            current = data[year][task]
            current["calls"] += 1
            current["task_window_ops"] += row.get("op", 0)
            attributed = [(y, val) for y, val in pending if y == year]
            current["reselect_calls"] += len(attributed)
            current["reselect_ops"] += sum(v for _, v in attributed)
            if sum(v for _, v in attributed) > row.get("op", 0):
                current["oversized_attributions"] += 1
            # Year boundary can be crossed by a long call. Never silently
            # assign events across years: count as unresolved separately.
            unassigned += sum(y != year for y, _ in pending)
            pending = []
    unassigned += len(pending)
    return {str(year): {task: dict(counts) for task, counts in data[year].items()}
            for year in YEARS}, unassigned


def run(folder, seeds):
    results = {}
    for seed in seeds:
        candidates = list(folder.glob(f"*seed{seed}_r0.log"))
        if len(candidates) != 1:
            raise ValueError(f"seed={seed}, expected one file: {len(candidates)}")
        with candidates[0].open(encoding="utf-8", errors="replace") as file:
            yearly, unassigned = parse(file)
        results[str(seed)] = {"years": yearly, "unassigned": unassigned}
    aggregate = {}
    for year in YEARS:
        record = {}
        keys = set().union(*(result["years"][str(year)] for result in results.values()))
        for task in sorted(keys):
            record[task] = {
                field: round(statistics.mean(
                    result["years"][str(year)].get(task, {}).get(field, 0)
                    for result in results.values()), 3)
                for field in ("calls", "task_window_ops", "reselect_calls", "reselect_ops",
                              "oversized_attributions")
            }
        aggregate[str(year)] = record
    return {"seeds": seeds, "by_seed": results, "average": aggregate,
            "notes": ["Only reselect calls preceding the next SCHED_IDLE line are attributed to that task.",
                      "Nested scheduler invocations could make order-based attribution ambiguous.",
                      "SCHED_IDLE's no_work classifier compares project object identity and vehicle count, not its best/candidateGroups contents.",
                      "These are measured window ops, not exclusively executed Squirrel VM instructions."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    args = parser.parse_args()
    d = run(args.logs, args.seeds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    for year in YEARS:
        x = d["average"][str(year)].get("air_fleet", {})
        print(f"{year} air_fleet calls={x.get('calls', 0):.1f} "
              f"ops={x.get('task_window_ops', 0)/1e6:.3f}M "
              f"reselect={x.get('reselect_ops', 0)/1e6:.3f}M "
              f"calls_reselect={x.get('reselect_calls', 0):.1f} "
              f"oversize={x.get('oversized_attributions', 0)}")


if __name__ == "__main__":
    main()
