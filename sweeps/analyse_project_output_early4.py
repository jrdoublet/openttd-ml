#!/usr/bin/env python3
"""Mesure descriptive de la variation positive nette des lignes et recherches P5.

P5_BUILD_LINE compte les deltas positifs NETS de _lines après dispatch,
pas toutes les nouvelles lignes brutes si des suppressions sont simultanées.
P5_RAIL_SEARCH contient des rappels de résultat à 0 ops : ne pas les
considérer comme de nouvelles recherches coûteuses. Budgets P5 inclus C39.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from analyse_opcode_early4 import DATE, LINE, YEARS, fields


def parse(stream):
    yearly = defaultdict(lambda: {
        "lines_by_mode": Counter(), "line_routes": set(),
        "lines_by_month": defaultdict(Counter),
        "search_outcome": Counter(), "search_positive_outcome": Counter(),
        "search_calls": 0, "search_paid_calls": 0,
        "search_window_ops": 0, "search_days": 0,
    })
    for raw in stream:
        m = LINE.search(raw)
        if not m:
            continue
        d = DATE.match(m[1])
        if not d:
            continue
        year, name, rest = int(d[1]), d[2], d[3]
        if year not in YEARS:
            continue
        f = fields(rest)
        stats = yearly[year]
        if name == "P5_BUILD_LINE":
            mode = str(f.get("mode", "unknown"))
            stats["lines_by_mode"][mode] += 1
            # OPEX date uses month from text. A repeated (src,dst) does not
            # necessarily imply a duplicate log or that line was unbuilt.
            month = m[1].split(" ", 2)[1].split("-")[1]
            stats["lines_by_month"][month][mode] += 1
            stats["line_routes"].add((mode, f.get("src"), f.get("dst")))
        elif name == "P5_RAIL_SEARCH":
            stats["search_calls"] += 1
            stats["search_outcome"][str(f.get("outcome", "unknown"))] += 1
            if f.get("ops", 0) > 0:
                stats["search_paid_calls"] += 1
                stats["search_positive_outcome"][str(f.get("outcome", "unknown"))] += 1
                stats["search_window_ops"] += f["ops"]
                stats["search_days"] += f.get("days", 0)
    return {str(year): {
        "lines_by_mode": dict(sorted(yearly[year]["lines_by_mode"].items())),
        "lines_by_month": {k: dict(sorted(v.items())) for k, v in sorted(yearly[year]["lines_by_month"].items())},
        "unique_mode_src_dst": len(yearly[year]["line_routes"]),
        "search_outcome": dict(sorted(yearly[year]["search_outcome"].items())),
        "search_paid_outcome": dict(sorted(yearly[year]["search_positive_outcome"].items())),
        "search_calls": yearly[year]["search_calls"],
        "search_paid_calls": yearly[year]["search_paid_calls"],
        "search_window_ops": yearly[year]["search_window_ops"],
        "search_days": yearly[year]["search_days"],
    } for year in YEARS}


def run(directory, seeds):
    records = {}
    for seed in seeds:
        candidates = list(directory.glob(f"*seed{seed}_r0.log"))
        if len(candidates) != 1:
            raise ValueError(f"seed={seed}, expected exactly one log")
        with candidates[0].open(encoding="utf8", errors="replace") as handle:
            records[str(seed)] = parse(handle)
    mean = {}
    for year in YEARS:
        record = {}
        modes = set().union(*(records[str(s)][str(year)]["lines_by_mode"] for s in seeds))
        for mode in sorted(modes):
            record["lines_" + mode] = round(statistics.mean(
                records[str(s)][str(year)]["lines_by_mode"].get(mode, 0) for s in seeds), 3)
        for key in ("search_calls", "search_paid_calls", "search_window_ops", "search_days"):
            record[key] = round(statistics.mean(records[str(s)][str(year)][key] for s in seeds), 3)
        mean[str(year)] = record
    return {"seeds": seeds, "by_seed": records, "mean": mean,
            "notes": [
                "Profiled logs differ economically from unsounded baseline; line counts are not from economic baseline.",
                "P5_BUILD_LINE emits only when _lines.len() increases during dispatch; one log per net-new line, not every gross build when simultaneous removals occur.",
                "P5_RAIL_SEARCH includes zero-op replays; only nonzero ops are summed, but they overlap C39.",
                "Other projects built, including fleet, do not produce P5_BUILD_LINE and cannot be inferred from line count.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("logs", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    a = p.parse_args()
    results = run(a.logs, a.seeds)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    for y, row in results["mean"].items():
        print(y, row)


if __name__ == "__main__":
    main()
