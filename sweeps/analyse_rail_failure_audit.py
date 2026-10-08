"""Count exact rail attempt events and pre-A* proximity refusals by kind.

Instrumented game timelines are diagnostic. Never use their economic differences
as uninstrumented policy qualification. Each emitted RAIL_AUDIT event is counted
once; recurring prechecks of the same OD are repeated *passes*.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

EVENT = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) RAIL_AUDIT (.*)$")
FIELD = re.compile(r"(\w+)=([^\s]+)")
LOG_NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")


def summarize(lines):
    counters = defaultdict(Counter)
    distinct = defaultdict(set)
    distinct_stage_kind = defaultdict(set)
    invalid = 0
    events = 0
    for line in lines:
        if "RAIL_AUDIT " not in line:
            continue
        m = EVENT.search(line.rstrip())
        if m is None:
            invalid += 1
            continue
        year = m.group(1)
        fields = dict(FIELD.findall(m.group(4)))
        if not all(fields.get(key) for key in ("stage", "kind", "cargo", "src", "dst", "reason", "ok")):
            invalid += 1
            continue
        if fields["stage"] not in ("attempt", "precheck") or fields["kind"] not in ("freight", "pax"):
            invalid += 1
            continue
        try:
            actual = int(fields.get("actual", "0"))
            ops = int(fields.get("ops", "0"))
            ok = int(fields["ok"])
        except ValueError:
            invalid += 1
            continue
        if ok not in (0, 1):
            invalid += 1
            continue
        events += 1
        kind = fields["kind"]
        stage = fields["stage"]
        reason = fields["reason"]
        cargo = fields["cargo"]
        key = (stage, kind, cargo, fields["src"], fields["dst"])
        counters[year][f"{stage}/{kind}/{reason}"] += 1
        counters[year][f"{stage}/{kind}/TOTAL"] += 1
        counters[year][f"cargo/{stage}/{kind}/{cargo}/{reason}"] += 1
        counters[year][f"money/{stage}/{kind}/{reason}"] += actual
        counters[year][f"opcodes/{stage}/{kind}/{reason}"] += ops
        distinct[year].add(key)
        distinct_stage_kind[(year, stage, kind)].add((cargo, fields["src"], fields["dst"]))
    return {"annual": {year: {"counts": dict(counter),
                               "distinct_stage_kind_cargo_od": len(distinct[year]),
                               "distinct_by_stage_kind": {
                                   f"{stage}/{kind}": len(pairs)
                                   for (yr, stage, kind), pairs in sorted(distinct_stage_kind.items())
                                   if yr == year}}
                       for year, counter in sorted(counters.items())},
            "event_count": events, "invalid_events": invalid}


def compare(log_dir: Path):
    arms = defaultdict(dict)
    for path in sorted(log_dir.glob("*.log")):
        m = LOG_NAME.match(path.name)
        if m is None:
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            row = summarize(handle)
        seed = int(m.group("seed"))
        repeat = int(m.group("repeat"))
        arms[m.group("arm")][f"{seed}/{repeat}"] = row
    annual = {}
    for arm, runs in arms.items():
        by_year = defaultdict(Counter)
        for run in runs.values():
            for year, detail in run["annual"].items():
                by_year[year].update(detail["counts"])
        annual[arm] = {year: dict(counts) for year, counts in sorted(by_year.items())}
    return {"warning": "Sonded game trajectories only; prechecks are repeated passes, not unique projects",
            "arms": {arm: dict(runs) for arm, runs in arms.items()}, "annual_totals": annual}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("engine_dir", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    report = compare(args.engine_dir)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
