#!/usr/bin/env python3
"""Summarise the dominant replay-vs-candidate C104 mismatches."""

from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys


path = Path(sys.argv[1])
candidate = sys.argv[2]
payload = json.loads(path.read_text(encoding="utf-8"))

groups = defaultdict(list)
seen = set()
for row in payload.get("rows") or []:
    for event in row.get("events") or []:
        replay = event.get("replay_id")
        chosen = event.get(candidate + "_id")
        if replay is None or chosen is None or replay == chosen:
            continue
        event_key = (
            event.get("seed"), event.get("year"), event.get("arm"), event.get("airport"),
            event.get("dist"), event.get("pax"), event.get("maxC"), replay, chosen,
        )
        if event_key in seen:
            continue
        seen.add(event_key)
        groups[f"{replay}->{chosen}"].append(event)


def med(rows, field):
    vals = [float(row[field]) for row in rows if isinstance(row.get(field), (int, float))]
    return round(statistics.median(vals), 6) if vals else None


out = {}
for transition, rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))[:20]:
    out[transition] = {
        "n": len(rows),
        "pax_median": med(rows, "pax"),
        "distance_median": med(rows, "dist"),
        "replay_capacity": med(rows, "replay_cap"),
        "candidate_capacity": med(rows, candidate + "_cap"),
        "replay_monthly_capacity": med(rows, "replay_mcap"),
        "candidate_monthly_capacity": med(rows, candidate + "_mcap"),
        "replay_carried": med(rows, "replay_carried"),
        "candidate_carried": med(rows, candidate + "_carried"),
        "replay_profit": med(rows, "replay_P"),
        "candidate_profit": med(rows, candidate + "_P"),
        "replay_days": med(rows, "replay_days"),
        "candidate_days": med(rows, candidate + "_days"),
    }

print(json.dumps(out, indent=2))
