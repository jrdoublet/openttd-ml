from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


DEFAULT = Path("results/smoke_c118_territorial_1x3_20260927_r3.jsonl")
POLICIES = ("reference", "c118_territorial")


def final_opex_rows(path: Path):
    latest = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("run", [None])[0] != "OpexAI":
                continue
            policy = row.get("duel_policy_id")
            if policy in POLICIES:
                latest[policy] = row
    return latest


def unique_curve(events):
    curve = []
    for event in events:
        point = (dt.date(event["year"], event["month"], event["day"]), event["towns"])
        if not curve or point[1] != curve[-1][1]:
            curve.append(point)
    return curve


def town_days(curve, start, end):
    total = 0
    covered = 0
    previous = start
    for date, towns in curve:
        if date < start:
            covered = towns
            continue
        if date > end:
            break
        total += (date - previous).days * covered
        previous = date
        covered = towns
    total += (end - previous).days * covered
    return total


def milestones(curve):
    result = {}
    previous = 0
    for date, towns in curve:
        if towns <= previous:
            continue
        for n in range(previous + 1, towns + 1):
            result[n] = date
        previous = towns
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT)
    args = parser.parse_args()
    rows = final_opex_rows(args.path)
    start = dt.date(1970, 1, 1)
    end = dt.date(1972, 12, 1)

    stats = {}
    for policy in POLICIES:
        row = rows[policy]
        curve = unique_curve(row.get("c118_coverage_events", []))
        days = town_days(curve, start, end)
        marks = milestones(curve)
        stats[policy] = (days, curve, marks, row)
        print(f"[{policy}] town_days={days} avg_towns={days / (end - start).days:.3f}")
        print("coverage", " ".join(f"{date}:{towns}" for date, towns in curve))
        print("milestones", " ".join(f"{n}:{marks[n]}" for n in sorted(marks)))
        print(
            "final",
            f"profit_year={row.get('profit_year')}",
            f"company_value={row.get('company_value')}",
            f"airports={row.get('air_airports')}",
            f"physical_towns={row.get('airport_towns_opex_present')}",
            f"air_fleet={row.get('air_primary_vehicles')}",
            f"pax_capacity={row.get('air_passenger_capacity')}",
            f"decisions={row.get('c118_decision_count', 0)}",
        )

    ref_days = stats["reference"][0]
    var_days = stats["c118_territorial"][0]
    print(f"delta_town_days={var_days - ref_days:+d}")
    ref = stats["reference"][3]
    var = stats["c118_territorial"][3]
    for field in ("profit_year", "company_value", "air_airports", "airport_towns_opex_present",
                  "air_primary_vehicles", "air_passenger_capacity"):
        r = ref.get(field) or 0
        v = var.get(field) or 0
        print(f"delta_{field}={v-r:+}")


if __name__ == "__main__":
    main()
