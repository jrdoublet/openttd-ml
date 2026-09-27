#!/usr/bin/env python3
"""Compare passive speed-regularised AIR choosers from a C104 diagnostic."""

import json
from pathlib import Path
import statistics
import sys


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
    }


def ratio(a, b):
    return float(a) / float(b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


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


def candidate(rows, prefix):
    rows = [e for e in rows if isinstance(e.get(prefix + "_id"), (int, float))]
    return {
        "events": len(rows),
        "vs_replay_disagree_pct": (
            100.0 * sum(e.get(prefix + "_id") != e.get("replay_id") for e in rows) / len(rows)
            if rows else None
        ),
        "vs_physical_disagree_pct": (
            100.0 * sum(e.get(prefix + "_id") != e.get("physical_id") for e in rows) / len(rows)
            if rows else None
        ),
        "price_over_legacy": stats(ratio(e.get(prefix + "_price"), e.get("legacy_price")) for e in rows),
        "speed_over_legacy": stats(ratio(e.get(prefix + "_speed"), e.get("legacy_speed")) for e in rows),
        "physical_profit_over_max": stats(ratio(e.get(prefix + "_P"), e.get("physical_P")) for e in rows),
        "physical_capital_over_max": stats(ratio(e.get(prefix + "_C"), e.get("physical_C")) for e in rows),
    }


prefixes = ("onestep", "s1", "s2", "s3", "s4", "e25", "e50", "e75", "e100")
result = {
    prefix: {
        "overall": candidate(events, prefix),
        "by_arm": {
            arm: candidate([e for e in events if e.get("arm") == arm], prefix)
            for arm in ("newpair", "hubsite", "hubhub")
        },
    }
    for prefix in prefixes
}
print(json.dumps(result, indent=2))
