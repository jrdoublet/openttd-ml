#!/usr/bin/env python3
"""Summarise static and economic AIR engine profiles from a C104 diagnostic."""

from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

path = Path(sys.argv[1])
wanted = {int(value) for value in sys.argv[2:]} if len(sys.argv) > 2 else None
payload = json.loads(path.read_text(encoding="utf-8"))
prefixes = (
    "legacy", "replay", "physical", "c69phys", "marginal", "onestep",
    "p7", "p8", "p9", "p10", "s1", "s2", "s3", "s4",
    "e25", "e50", "e75", "e100",
    "replay_legacy", "replay_physical", "physical_legacy", "physical_replay",
    "marginal_legacy",
)
values = defaultdict(lambda: defaultdict(list))
seen = set()
for row in payload.get("rows") or []:
    for event in row.get("events") or []:
        event_key = (event.get("seed"), event.get("year"), event.get("arm"), event.get("airport"), event.get("dist"), event.get("pax"), event.get("maxC"))
        for prefix in prefixes:
            engine = event.get(prefix + "_id")
            if not isinstance(engine, int) or engine < 0 or (wanted is not None and engine not in wanted):
                continue
            key = (event_key, prefix, engine)
            if key in seen:
                continue
            seen.add(key)
            for field in ("price", "cap", "speed", "n", "P", "R", "run", "amort", "C", "imm", "roi", "days", "trips", "rating", "mcap", "carried"):
                value = event.get(prefix + "_" + field)
                if isinstance(value, (int, float)):
                    values[engine][field].append(float(value))

def summary(vals):
    if not vals:
        return None
    return {"n": len(vals), "median": round(statistics.median(vals), 6), "mean": round(statistics.mean(vals), 6), "min": round(min(vals), 6), "max": round(max(vals), 6)}

print(json.dumps({str(engine): {field: summary(vals) for field, vals in sorted(fields.items())} for engine, fields in sorted(values.items())}, indent=2))
