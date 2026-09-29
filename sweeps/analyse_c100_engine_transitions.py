#!/usr/bin/env python3
"""Match C98 events between first C100 and C100.1 at identical route context."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics


def load_events(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = []
    for row in payload.get("rows") or []:
        seed = row.get("seed")
        for event in row.get("events") or []:
            e = dict(event)
            e["seed"] = seed
            events.append(e)
    return events


def key(e):
    return (e.get("seed"), e.get("year"), e.get("arm"), e.get("distance"), e.get("monthly_pax"))


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def ratio(a, b):
    return (a / b) if a is not None and b not in (None, 0) else None


def unique_event(rows):
    by_sig = {}
    for e in rows:
        sig = (
            e.get("engine"), e.get("pred_p"), e.get("pred_r"), e.get("pred_days"),
            e.get("pred_n"), e.get("engine_price"), e.get("engine_capacity"),
        )
        by_sig[sig] = e
    return next(iter(by_sig.values())) if len(by_sig) == 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()
    a = load_events(args.first)
    b = load_events(args.second)
    ia, ib = defaultdict(list), defaultdict(list)
    for e in a: ia[key(e)].append(e)
    for e in b: ib[key(e)].append(e)
    pairs = []
    ambiguous = 0
    for k in set(ia) & set(ib):
        x = unique_event(ia[k])
        y = unique_event(ib[k])
        if x is None or y is None:
            ambiguous += 1
            continue
        pairs.append((x, y))
    changed = [(x, y) for x, y in pairs if x.get("engine") != y.get("engine")]
    transitions = Counter((x.get("engine"), y.get("engine")) for x, y in changed)
    by_transition = {}
    for trans, n in transitions.most_common():
        rows = [(x, y) for x, y in changed if (x.get("engine"), y.get("engine")) == trans]
        by_transition[f"{trans[0]}->{trans[1]}"] = {
            "n": n,
            "price_ratio": median(ratio(y.get("engine_price"), x.get("engine_price")) for x, y in rows),
            "capacity_ratio": median(ratio(y.get("engine_capacity"), x.get("engine_capacity")) for x, y in rows),
            "pred_n_ratio": median(ratio(y.get("pred_n"), x.get("pred_n")) for x, y in rows),
            "fleet_purchase_ratio": median(ratio((y.get("engine_price") or 0) * (y.get("pred_n") or 0), (x.get("engine_price") or 0) * (x.get("pred_n") or 0)) for x, y in rows),
            "pred_profit_ratio": median(ratio(y.get("pred_p"), x.get("pred_p")) for x, y in rows),
            "pred_days_delta": median((y.get("pred_days") or 0) - (x.get("pred_days") or 0) for x, y in rows),
            "trips_pm_ratio": median(ratio(y.get("pred_trips_pm"), x.get("pred_trips_pm")) for x, y in rows),
            "distance_median": median(x.get("distance") for x, _ in rows),
            "monthly_pax_median": median(x.get("monthly_pax") for x, _ in rows),
            "arms": dict(Counter(x.get("arm") for x, _ in rows)),
        }
    print(json.dumps({
        "matched_unique_contexts": len(pairs),
        "ambiguous_contexts_skipped": ambiguous,
        "engine_changed": len(changed),
        "engine_changed_pct": 100.0 * len(changed) / len(pairs) if pairs else None,
        "transitions": {f"{u}->{v}": n for (u, v), n in transitions.most_common()},
        "by_transition": by_transition,
        "all_changed": {
            "price_ratio": median(ratio(y.get("engine_price"), x.get("engine_price")) for x, y in changed),
            "fleet_purchase_ratio": median(ratio((y.get("engine_price") or 0) * (y.get("pred_n") or 0), (x.get("engine_price") or 0) * (x.get("pred_n") or 0)) for x, y in changed),
            "pred_profit_ratio": median(ratio(y.get("pred_p"), x.get("pred_p")) for x, y in changed),
            "pred_days_delta": median((y.get("pred_days") or 0) - (x.get("pred_days") or 0) for x, y in changed),
            "trips_pm_ratio": median(ratio(y.get("pred_trips_pm"), x.get("pred_trips_pm")) for x, y in changed),
        },
    }, indent=2))


if __name__ == "__main__":
    main()
