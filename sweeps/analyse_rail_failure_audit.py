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
POOL_EVENT = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) RAIL_POOL_AUDIT (.*)$")
BLOCKER_EVENT = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) RAIL_BLOCKER (.*)$")
FIELD = re.compile(r"(\w+)=([^\s]+)")
LOG_NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")


def summarize(lines):
    counters = defaultdict(Counter)
    blockers = defaultdict(Counter)
    blocker_maxima = defaultdict(lambda: defaultdict(dict))
    distinct = defaultdict(set)
    distinct_stage_kind = defaultdict(set)
    pool_sums = defaultdict(lambda: defaultdict(Counter))
    invalid_pool = 0
    invalid_blocker = 0
    invalid = 0
    events = 0
    for line in lines:
        if "RAIL_BLOCKER " in line:
            m = BLOCKER_EVENT.search(line.rstrip())
            if m is None:
                invalid_blocker += 1
                continue
            fields = dict(FIELD.findall(m.group(4)))
            requested = fields.get("requested_kind")
            owner = fields.get("blocker")
            phase = fields.get("phase")
            if requested not in ("pax", "freight") or owner not in ("primary", "upgrade") or phase not in ("search", "build"):
                invalid_blocker += 1
                continue
            key = f"{requested}/{owner}/{phase}"
            blockers[m.group(1)][key] += 1
            for field in ("age_days", "spent", "budget"):
                try:
                    value = int(fields[field])
                except (KeyError, ValueError):
                    invalid_blocker += 1
                    break
                existing = blocker_maxima[m.group(1)][key].get(field)
                if existing is None or value > existing:
                    blocker_maxima[m.group(1)][key][field] = value
            continue
        if "RAIL_POOL_AUDIT " in line:
            m = POOL_EVENT.search(line.rstrip())
            if m is None:
                invalid_pool += 1
                continue
            values = dict(FIELD.findall(m.group(4)))
            phase = values.get("phase")
            if phase not in ("full", "incremental", "reselect"):
                invalid_pool += 1
                continue
            try:
                metrics = {
                    key: int(values[key]) for key in
                    ("pax", "freight", "affordable_pax", "affordable_freight",
                     "selected_pax", "selected_freight", "selected_air",
                     "selected_fleet", "dropped_pax", "dropped_freight")
                }
            except (KeyError, ValueError):
                invalid_pool += 1
                continue
            values = pool_sums[m.group(1)][phase]
            values["calls"] += 1
            values.update(metrics)
            head_mode = dict(FIELD.findall(m.group(4))).get("head_mode", "-")
            head_kind = dict(FIELD.findall(m.group(4))).get("head_kind", "-")
            if head_mode not in ("rail", "air", "fleet", "road", "water", "-"):
                head_mode = "unknown"
            values["head/" + head_mode] += 1
            if head_mode == "rail":
                values["head/rail/" + (head_kind if head_kind in ("pax", "freight") else "other")] += 1
            continue
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
        if fields["stage"] not in ("attempt", "precheck", "dispatch", "early") or fields["kind"] not in ("freight", "pax"):
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
            "pool_annual": {yr: {phase: dict(metrics) for phase, metrics in sorted(phases.items())}
                            for yr, phases in sorted(pool_sums.items())},
            "blocker_annual": {yr: {"counts": dict(blockers[yr]),
                                     "maxima": dict(blocker_maxima[yr])}
                               for yr in sorted(blockers)},
            "event_count": events, "invalid_events": invalid,
            "invalid_pool_events": invalid_pool, "invalid_blocker_events": invalid_blocker}


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
    annual_pools = {}
    annual_blockers = {}
    for arm, runs in arms.items():
        by_year = defaultdict(Counter)
        by_pool = defaultdict(lambda: defaultdict(Counter))
        by_blocker = defaultdict(Counter)
        for run in runs.values():
            for year, detail in run["annual"].items():
                by_year[year].update(detail["counts"])
            for year, phases in run["pool_annual"].items():
                for phase, metrics in phases.items():
                    by_pool[year][phase].update(metrics)
            for year, block in run["blocker_annual"].items():
                by_blocker[year].update(block["counts"])
        annual[arm] = {year: dict(counts) for year, counts in sorted(by_year.items())}
        annual_pools[arm] = {
            year: {phase: dict(metrics) for phase, metrics in sorted(phases.items())}
            for year, phases in sorted(by_pool.items())}
        annual_blockers[arm] = {year: dict(counts) for year, counts in sorted(by_blocker.items())}
    return {"warning": "Sonded game trajectories only; prechecks are repeated passes, not unique projects",
            "arms": {arm: dict(runs) for arm, runs in arms.items()},
            "annual_totals": annual, "annual_pool_totals": annual_pools,
            "annual_blocker_totals": annual_blockers}


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
