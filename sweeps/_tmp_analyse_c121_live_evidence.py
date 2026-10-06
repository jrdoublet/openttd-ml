#!/usr/bin/env python3
"""Screen passive C121 1->2 live-evidence rules from the existing C117 run."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def flatten(payload):
    events = []
    for row in payload.get("rows", []):
        seed = row.get("seed")
        for raw in row.get("events", []):
            e = dict(raw)
            e["seed"] = seed
            events.append(e)
    return events


def rolling(rows, idx, window_days):
    cur = rows[idx]
    lo = cur["age_days"] - window_days
    recent = [e for e in rows[: idx + 1] if e["age_days"] > lo]
    days = sum(max(1, int(e.get("period_days", 0) or 0)) for e in recent)
    trips = sum(int(e.get("trips", 0) or 0) for e in recent)
    trips_a = sum(int(e.get("trips_a", 0) or 0) for e in recent)
    trips_b = sum(int(e.get("trips_b", 0) or 0) for e in recent)
    profit = sum(float(e.get("profit", 0) or 0) for e in recent)
    pax = sum(float(e.get("pax", 0) or 0) for e in recent)
    seats = sum(float(e.get("seat_legs", 0) or 0) for e in recent)
    load = pax / seats if seats > 0 else -1.0
    weighted = max(1, sum(int(e.get("samples", 0) or 0) for e in recent))
    wait_a = sum(float(e.get("wait_a", 0) or 0) * int(e.get("samples", 0) or 0) for e in recent) / weighted
    wait_b = sum(float(e.get("wait_b", 0) or 0) * int(e.get("samples", 0) or 0) for e in recent) / weighted
    cap = float(cur.get("cap_last", 0) or 0)
    wait_norm = max(wait_a, wait_b) / cap if cap > 0 else -1.0
    profit_pm = profit * 30.4 / days if days > 0 else 0.0
    return {
        "window_days": window_days,
        "covered_days": days,
        "trips": trips,
        "trips_a": trips_a,
        "trips_b": trips_b,
        "profit": profit,
        "profit_pm": profit_pm,
        "load": load,
        "wait_norm": wait_norm,
        "wait_a": wait_a,
        "wait_b": wait_b,
    }


RULES = {
    "balanced90": lambda age, r: age >= 60 and r["covered_days"] >= 50 and r["trips"] >= 2
        and r["profit"] > 0 and (r["load"] >= 0.40 or r["wait_norm"] >= 0.50),
    "strict90": lambda age, r: age >= 75 and r["covered_days"] >= 60 and r["trips"] >= 2
        and r["trips_a"] >= 1 and r["trips_b"] >= 1 and r["profit"] > 0
        and (r["load"] >= 0.55 or r["wait_norm"] >= 0.75),
    "dual_signal90": lambda age, r: age >= 60 and r["covered_days"] >= 50 and r["trips"] >= 2
        and r["profit"] > 0 and r["load"] >= 0.30 and r["wait_norm"] >= 0.25,
    "balanced60": lambda age, r: age >= 60 and r["covered_days"] >= 45 and r["trips"] >= 2
        and r["profit"] > 0 and (r["load"] >= 0.40 or r["wait_norm"] >= 0.50),
}


def future_label(rows, idx):
    age = rows[idx]["age_days"]
    future = [e for e in rows[idx + 1 :] if e["age_days"] <= age + 180]
    profit = sum(float(e.get("profit", 0) or 0) for e in future)
    days = sum(max(1, int(e.get("period_days", 0) or 0)) for e in future)
    return {
        "future_windows": len(future),
        "future_profit_pm": profit * 30.4 / days if days else None,
        "future_positive": profit > 0 if future else None,
        "eventual_two_planes": any(float(e.get("live_last", 0) or 0) >= 2 for e in rows[idx + 1 :]),
    }


def summarize(candidates):
    if not candidates:
        return {"n": 0}
    ages = [c["age_days"] for c in candidates]
    future = [c["future_profit_pm"] for c in candidates if c["future_profit_pm"] is not None]
    return {
        "n": len(candidates),
        "seeds": dict(sorted((str(s), sum(c["seed"] == s for c in candidates)) for s in {c["seed"] for c in candidates})),
        "age_mean": round(statistics.mean(ages), 1),
        "age_median": statistics.median(ages),
        "age_min": min(ages),
        "age_max": max(ages),
        "future_positive": sum(c["future_positive"] is True for c in candidates),
        "future_negative": sum(c["future_positive"] is False for c in candidates),
        "future_unknown": sum(c["future_positive"] is None for c in candidates),
        "eventual_two_planes": sum(c["eventual_two_planes"] for c in candidates),
        "future_profit_pm_mean": round(statistics.mean(future), 1) if future else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", nargs="?", type=Path,
        default=Path("results/c121_cadence_c117_2x3_20261001_r1.json"),
    )
    args = parser.parse_args()
    payload = json.loads(args.source.read_text(encoding="utf-8"))
    grouped = defaultdict(list)
    for e in flatten(payload):
        if e.get("line") is None or e.get("age_days") is None:
            continue
        grouped[(e["seed"], e["line"])].append(e)
    for rows in grouped.values():
        rows.sort(key=lambda e: e["age_days"])

    rule_windows = {"balanced60": 60, "balanced90": 90, "strict90": 90, "dual_signal90": 90}
    hits = {name: [] for name in RULES}
    eligible_lines = 0
    for (seed, line), rows in sorted(grouped.items()):
        if not any(60 <= e["age_days"] <= 240 and float(e.get("live_last", 0) or 0) == 1 for e in rows):
            continue
        eligible_lines += 1
        for name, rule in RULES.items():
            window = rule_windows[name]
            for i, e in enumerate(rows):
                age = int(e["age_days"])
                if age > 240 or float(e.get("live_last", 0) or 0) != 1:
                    continue
                r = rolling(rows, i, window)
                if rule(age, r):
                    hit = {
                        "seed": seed,
                        "line": line,
                        "arm": e.get("arm"),
                        "age_days": age,
                        "target_n": e.get("c121_target_n"),
                        **{k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()},
                        **future_label(rows, i),
                    }
                    hits[name].append(hit)
                    break

    result = {
        "source": str(args.source),
        "source_health": payload.get("health"),
        "lines_total": len(grouped),
        "eligible_one_plane_lines_60_240d": eligible_lines,
        "rules": {name: summarize(rows) for name, rows in hits.items()},
        "candidates": hits,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
