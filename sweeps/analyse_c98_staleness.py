#!/usr/bin/env python3
"""C98: bias predicted/realized by line age and station sharing."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def ratio(real, real_n, pred, pred_n):
    vals = (real, real_n, pred, pred_n)
    if not all(isinstance(v, (int, float)) for v in vals) or real_n <= 0 or pred_n <= 0 or pred == 0:
        return None
    return (real / real_n) / (pred / pred_n)


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    seen = {}
    for row in payload.get("rows", []):
        for event in row.get("events", []):
            seen[(event.get("seed"), event.get("profit_year"), event.get("line"))] = event
    buckets = {"age": defaultdict(list), "routes": defaultdict(list)}
    for e in seen.values():
        age = e.get("age")
        if not isinstance(age, (int, float)) or age < 1 or e.get("pred_capacity") != e.get("engine_capacity"):
            continue
        routes = [v for v in (e.get("live_routes_a"), e.get("live_routes_b")) if isinstance(v, (int, float))]
        if not routes:
            continue
        item = {
            "profit": ratio(e.get("real_p"), e.get("real_n"), e.get("pred_p"), e.get("pred_n")),
            "revenue": ratio(e.get("real_r"), e.get("real_n"), e.get("pred_r"), e.get("pred_n")),
        }
        buckets["age"][str(age)].append(item)
        buckets["routes"][str(max(routes))].append(item)
    out = {}
    for section, groups in buckets.items():
        out[section] = {key: {"n": len(items),
                              "profit_ratio": stats(x["profit"] for x in items),
                              "revenue_ratio": stats(x["revenue"] for x in items)}
                        for key, items in sorted(groups.items())}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
