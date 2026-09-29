#!/usr/bin/env python3
"""Agrège les bascules C68 -> C101 depuis la sonde C69 brute."""

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


def stats(values):
    values = [float(v) for v in values]
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    rows = []
    for line in args.path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("phase") == "c101_choice":
            rows.append(row)

    def ratio(a, b):
        a, b = float(a), float(b)
        return a / b if b else None

    price = [ratio(r["pick_price"], r["raw_price"]) for r in rows]
    capital = [ratio(r["pick_legacy_C"], r["raw_C"]) for r in rows]
    legacy_profit = [ratio(r["pick_legacy_P"], r["raw_P"]) for r in rows]
    price = [v for v in price if v is not None]
    capital = [v for v in capital if v is not None]
    legacy_profit = [v for v in legacy_profit if v is not None]
    transitions = Counter((str(r["raw_id"]), str(r["pick_id"])) for r in rows)
    out = {
        "n": len(rows),
        "price_ratio_pick_over_raw": stats(price),
        "capital_ratio_pick_over_raw": stats(capital),
        "legacy_profit_ratio_pick_over_raw": stats(legacy_profit),
        "pick_more_expensive_pct": 100.0 * sum(v > 1 for v in price) / len(price) if price else None,
        "pick_more_capital_pct": 100.0 * sum(v > 1 for v in capital) / len(capital) if capital else None,
        "pick_lower_legacy_profit_pct": 100.0 * sum(v < 1 for v in legacy_profit) / len(legacy_profit) if legacy_profit else None,
        "top_transitions": [
            {"raw": raw, "pick": pick, "count": count}
            for (raw, pick), count in transitions.most_common(20)
        ],
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
