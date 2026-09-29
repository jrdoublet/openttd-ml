#!/usr/bin/env python3
"""Aggregate latest per-seed AIR engine stats from an existing diagnostic JSON."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))

    latest = {}
    for row in payload.get("rows", []):
        key = (row.get("arm"), row.get("seed"))
        date = str(row.get("date") or "")
        if key not in latest or date > str(latest[key].get("date") or ""):
            latest[key] = row

    aggregate = defaultdict(lambda: defaultdict(lambda: {
        "count": 0, "profit": 0.0, "book": 0.0,
        "pax": 0.0, "mail": 0.0, "seeds": set(),
    }))
    totals = defaultdict(lambda: {"count": 0, "profit": 0.0, "seeds": set()})
    for (arm, seed), row in latest.items():
        for engine, values in (row.get("air_engine_stats") or {}).items():
            out = aggregate[str(arm)][str(engine)]
            count = int(values.get("count") or 0)
            profit = float(values.get("profit_this_year") or 0.0)
            out["count"] += count
            out["profit"] += profit
            out["book"] += float(values.get("book_value") or 0.0)
            out["pax"] += float(values.get("passenger_capacity") or 0.0)
            out["mail"] += float(values.get("mail_capacity") or 0.0)
            out["seeds"].add(seed)
            totals[str(arm)]["count"] += count
            totals[str(arm)]["profit"] += profit
            totals[str(arm)]["seeds"].add(seed)

    result = {"source": str(args.path), "arms": {}}
    for arm, engines in sorted(aggregate.items()):
        total = totals[arm]
        arm_out = {
            "aircraft": total["count"],
            "profit_this_year": round(total["profit"], 3),
            "profit_per_aircraft": round(total["profit"] / total["count"], 3) if total["count"] else None,
            "seeds": sorted(total["seeds"]),
            "engines": {},
        }
        for engine, values in sorted(engines.items(), key=lambda item: int(item[0])):
            count = values["count"]
            arm_out["engines"][engine] = {
                "count": count,
                "share_pct": round(100.0 * count / total["count"], 3) if total["count"] else None,
                "profit_per_aircraft": round(values["profit"] / count, 3) if count else None,
                "book_value_per_aircraft": round(values["book"] / count, 3) if count else None,
                "passenger_capacity_per_aircraft": round(values["pax"] / count, 3) if count else None,
                "mail_capacity_per_aircraft": round(values["mail"] / count, 3) if count else None,
                "seeds": sorted(values["seeds"]),
            }
        result["arms"][arm] = arm_out

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
