#!/usr/bin/env python3
"""Detailed transition stats from a saved C104 diagnostic JSON."""

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics
import sys


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None}
    return {"n": len(values), "mean": statistics.mean(values), "median": statistics.median(values)}


def ratio(a, b):
    return a / b if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
unique = {}
for row in payload.get("rows") or []:
    for e in row.get("events") or []:
        key = (e.get("seed"), e.get("arm"), e.get("airport"), e.get("dist"), e.get("pax"),
               e.get("maxC"), e.get("legacy_id"), e.get("replay_id"), e.get("physical_id"))
        unique[key] = e
events = list(unique.values())
groups = defaultdict(list)
for e in events:
    if e.get("replay_id") != e.get("physical_id"):
        groups[f"{e.get('replay_id')}->{e.get('physical_id')}"] .append(e)

out = {}
for name, rows in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    marginal_roi = []
    marginal_over_base_roi = []
    alpha_indifference = []
    for e in rows:
        if all(isinstance(e.get(k), (int, float)) for k in ("physical_P", "replay_physical_P", "physical_C", "replay_physical_C")):
            dp = e["physical_P"] - e["replay_physical_P"]
            dc = e["physical_C"] - e["replay_physical_C"]
            if dc > 0:
                mroi = dp * 1000.0 / dc
                marginal_roi.append(mroi)
                base_roi = e.get("replay_physical_roi")
                if isinstance(base_roi, (int, float)) and base_roi > 0:
                    marginal_over_base_roi.append(mroi / base_roi)
        p_big = e.get("physical_P")
        p_small = e.get("replay_physical_P")
        c_big = e.get("physical_C")
        c_small = e.get("replay_physical_C")
        if (isinstance(p_big, (int, float)) and isinstance(p_small, (int, float))
                and isinstance(c_big, (int, float)) and isinstance(c_small, (int, float))
                and p_big > p_small > 0 and c_big > c_small > 0):
            alpha_indifference.append(math.log(p_big / p_small) / math.log(c_big / c_small))
    out[name] = {
        "n": len(rows),
        "arms": dict(Counter(str(e.get("arm")) for e in rows)),
        "price_ratio": stats(ratio(e.get("physical_price"), e.get("replay_price")) for e in rows),
        "capital_ratio": stats(ratio(e.get("physical_C"), e.get("replay_physical_C")) for e in rows),
        "physical_profit_gain": stats(e.get("physical_P") - e.get("replay_physical_P") for e in rows),
        "physical_capital_gain": stats(e.get("physical_C") - e.get("replay_physical_C") for e in rows),
        "marginal_roi_permille": stats(marginal_roi),
        "marginal_over_replay_physical_roi": stats(marginal_over_base_roi),
        "alpha_indifference_profit_over_capital": stats(alpha_indifference),
        "replay_penalty_of_physical": stats(e.get("physical_replay_P") - e.get("replay_P") for e in rows),
        "legacy_profit_replay": stats(e.get("replay_legacy_P") for e in rows),
        "legacy_profit_physical": stats(e.get("physical_legacy_P") for e in rows),
        "days_gain_physical": stats(e.get("physical_days") - e.get("replay_physical_days") for e in rows),
        "distance": stats(e.get("dist") for e in rows),
        "pax": stats(e.get("pax") for e in rows),
    }

print(json.dumps(out, indent=2))
