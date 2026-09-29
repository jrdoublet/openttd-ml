#!/usr/bin/env python3
"""Summarise C106 marginal choice from a C104 JSON containing marginal_legacy fields."""

import json
from pathlib import Path
import statistics
import sys


def ratio_stats(rows, numerator, denominator):
    values = []
    for row in rows:
        a = row.get(numerator)
        b = row.get(denominator)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b:
            values.append(float(a) / float(b))
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
    }


payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
unique = {}
for row in payload.get("rows") or []:
    for event in row.get("events") or []:
        key = (
            event.get("seed"), event.get("year"), event.get("arm"), event.get("airport"),
            event.get("dist"), event.get("pax"), event.get("maxC"),
        )
        unique[key] = event
events = list(unique.values())


def summarise(rows):
    switched = [e for e in rows if e.get("marginal_id") != e.get("legacy_id")]
    return {
        "events": len(rows),
        "switches": len(switched),
        "switch_pct": 100.0 * len(switched) / len(rows) if rows else None,
        "vs_replay_disagree_pct": (
            100.0 * sum(e.get("marginal_id") != e.get("replay_id") for e in rows) / len(rows)
            if rows else None
        ),
        "price_over_legacy": ratio_stats(switched, "marginal_price", "legacy_price"),
        "speed_over_legacy": ratio_stats(switched, "marginal_speed", "legacy_speed"),
        "legacy_profit_over_legacy": ratio_stats(switched, "marginal_legacy_P", "legacy_P"),
        "legacy_capital_over_legacy": ratio_stats(switched, "marginal_legacy_C", "legacy_C"),
    }


result = {
    "overall": summarise(events),
    "by_arm": {
        arm: summarise([e for e in events if e.get("arm") == arm])
        for arm in ("newpair", "hubsite", "hubhub")
    },
    "by_year": {
        str(year): summarise([e for e in events if e.get("year") == year])
        for year in sorted({e.get("year") for e in events if isinstance(e.get("year"), int)})
    },
}
print(json.dumps(result, indent=2))
