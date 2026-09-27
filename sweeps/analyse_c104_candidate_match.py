#!/usr/bin/env python3
"""C104: compact candidate-to-replay engine-choice agreement summary."""

from collections import Counter
import json
from pathlib import Path
import sys


path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))

unique = {}
for row in payload.get("rows") or []:
    for event in row.get("events") or []:
        key = (
            event.get("seed"), event.get("year"), event.get("arm"), event.get("airport"),
            event.get("dist"), event.get("pax"), event.get("maxC"),
        )
        unique[key] = event

events = list(unique.values())
candidates = (
    "legacy", "physical", "c69phys", "marginal", "onestep",
    "p7", "p8", "p9", "p10", "s1", "s2", "s3", "s4",
    "e25", "e50", "e75", "e100",
)
if len(sys.argv) > 2:
    requested = tuple(sys.argv[2:])
    unknown = [name for name in requested if name not in candidates]
    if unknown:
        raise SystemExit(f"unknown candidate(s): {', '.join(unknown)}")
    candidates = requested

out = {"events": len(events), "candidates": {}}
for name in candidates:
    comparable = [
        event for event in events
        if event.get("replay_id") is not None and event.get(name + "_id") is not None
    ]
    matches = sum(event.get("replay_id") == event.get(name + "_id") for event in comparable)
    engine_mix = Counter(str(event.get(name + "_id")) for event in comparable)
    replay_mix = Counter(str(event.get("replay_id")) for event in comparable)
    mismatches = Counter(
        f"{event.get('replay_id')}->{event.get(name + '_id')}"
        for event in comparable
        if event.get("replay_id") != event.get(name + "_id")
    )
    out["candidates"][name] = {
        "n": len(comparable),
        "match": matches,
        "match_pct": round(100.0 * matches / len(comparable), 3) if comparable else None,
        "engine_mix": dict(engine_mix.most_common()),
        "replay_mix": dict(replay_mix.most_common()),
        "top_mismatches": dict(mismatches.most_common(20)),
    }

print(json.dumps(out, indent=2))
