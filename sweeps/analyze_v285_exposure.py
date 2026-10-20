#!/usr/bin/env python3
"""Audit de l'exposition V285 : logs moteur (DECISION_LOG) par graine.

L'evenement action=wagon est une tentative ; seul V285_RESULT action=moved
prouve qu'un wagon a ete attache physiquement au train. Un resume_failed apres
moved ne retire pas le wagon. Ne jamais assimiler l'absence de logs a zero.
"""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import json
from pathlib import Path
import re


LOG_NAME = re.compile(r"^(?P<policy>[^_]+)_seed(?P<seed>\d+)_r\d+\.log(?:\.gz)?$")
EVENT = re.compile(r"\[0\]\s+\[I\]\s+OPEX\s+(?P<date>\d+-\d+-\d+)\s+(?P<kind>V285|V285_GATE|V285_RESULT)\s+(?P<fields>.*)")
FIELDS = re.compile(r"([a-z_]+)=([^\s]+)")


def summarize_lines(lines):
    result = Counter()
    gates = Counter()
    lines_moved = Counter()
    attempt_dates = defaultdict(list)
    for line in lines:
        match = EVENT.search(line)
        if not match:
            continue
        fields = dict(FIELDS.findall(match.group("fields")))
        kind = match.group("kind")
        if kind == "V285" and fields.get("action") == "wagon":
            result["attempts"] += 1
            attempt_dates[fields.get("line", "?")].append(date(*map(int, match.group("date").split("-"))))
        elif kind == "V285_RESULT":
            action = fields.get("action", "unknown")
            result[action] += 1
            if action == "moved":
                lines_moved[fields.get("line", "?")] += 1
                result["wagon_cost"] += int(fields.get("cost", "0"))
        elif kind == "V285_GATE":
            gates[fields.get("reason", "unknown")] += 1
    result["distinct_lines_moved"] = len(lines_moved)
    gaps = [int((dates[i] - dates[i-1]).days)
            for dates in attempt_dates.values() for i in range(1, len(dates))]
    result["cooldown_violations"] = sum(gap < 90 for gap in gaps)
    result["min_repeated_attempt_gap_days"] = min(gaps) if gaps else None
    return result, gates, lines_moved


def read_log(path):
    if path.suffix == ".gz":
        import gzip
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
            return summarize_lines(stream)
    with path.open(encoding="utf-8", errors="replace") as stream:
        return summarize_lines(stream)


def analyze(log_dir, policy):
    rows = []
    for path in sorted(log_dir.glob("*_seed*_r*.log*")):
        match = LOG_NAME.match(path.name)
        if not match or match.group("policy") != policy:
            continue
        counts, gates, lines_moved = read_log(path)
        rows.append({
            "seed": int(match.group("seed")), "attempts": counts["attempts"],
            "moved": counts["moved"], "completed": counts["completed"],
            "resume_failed": counts["resume_failed"], "failed": counts["failed"],
            "wagon_cost": counts["wagon_cost"],
            "distinct_lines_moved": counts["distinct_lines_moved"],
            "cooldown_violations": counts["cooldown_violations"],
            "min_repeated_attempt_gap_days": counts["min_repeated_attempt_gap_days"],
            "gates": dict(sorted(gates.items())),
            "moves_by_line": dict(sorted(lines_moved.items())),
        })
    return sorted(rows, key=lambda row: row["seed"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--policy", default="v285")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--expected-seeds", type=int)
    args = parser.parse_args()
    rows = analyze(args.engine_dir, args.policy)
    if not rows or (args.expected_seeds is not None and len(rows) != args.expected_seeds):
        parser.error(f"journaux insuffisants : {len(rows)} graines, attendues {args.expected_seeds}")
    summary = {k: sum(row[k] for row in rows) for k in
               ("attempts", "moved", "completed", "resume_failed", "failed", "wagon_cost", "cooldown_violations")}
    summary["seeds"] = len(rows)
    summary["seeds_with_moved"] = sum(row["moved"] > 0 for row in rows)
    summary["gates"] = dict(sorted(sum((Counter(r["gates"]) for r in rows), Counter()).items()))
    report = {"policy": args.policy, "summary": summary, "by_seed": rows,
              "note": "moved = wagon physique; attempts = decision; les logs exigent decision_log=1"}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[k for k in rows[0] if k not in ("gates", "moves_by_line")])
            writer.writeheader()
            writer.writerows({k: v for k, v in row.items() if k not in ("gates", "moves_by_line")} for row in rows)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
