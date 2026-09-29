#!/usr/bin/env python3
import json, statistics, sys
from pathlib import Path

def stats(vals):
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    return {"n": len(vals), "mean": statistics.mean(vals) if vals else None, "median": statistics.median(vals) if vals else None}

def ratio(a, b):
    return float(a) / float(b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
u = {}
for row in d.get("rows") or []:
    for e in row.get("events") or []:
        u[(e.get("seed"), e.get("year"), e.get("arm"), e.get("airport"), e.get("dist"), e.get("pax"), e.get("maxC"))] = e
events = list(u.values())

def summary(rows):
    rows = [e for e in rows if isinstance(e.get("onestep_id"), (int, float))]
    switched = [e for e in rows if e.get("onestep_id") != e.get("physical_id")]
    return {
        "events": len(rows),
        "switch_from_physical_pct": 100.0 * len(switched) / len(rows) if rows else None,
        "vs_replay_disagree_pct": 100.0 * sum(e.get("onestep_id") != e.get("replay_id") for e in rows) / len(rows) if rows else None,
        "price_over_legacy": stats(ratio(e.get("onestep_price"), e.get("legacy_price")) for e in rows),
        "speed_over_legacy": stats(ratio(e.get("onestep_speed"), e.get("legacy_speed")) for e in rows),
        "physical_profit_over_max": stats(ratio(e.get("onestep_P"), e.get("physical_P")) for e in rows),
        "physical_capital_over_max": stats(ratio(e.get("onestep_C"), e.get("physical_C")) for e in rows),
    }

print(json.dumps({"overall": summary(events), "by_arm": {a: summary([e for e in events if e.get("arm") == a]) for a in ("newpair", "hubsite", "hubhub")}}, indent=2))
