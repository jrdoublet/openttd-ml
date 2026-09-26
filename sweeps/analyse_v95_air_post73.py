#!/usr/bin/env python3
"""Resume l'exposition V95 AIR post-1973 par famille et par etat de slot."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


FIELDS = ("pop", "pax_prod", "mail_prod", "pax_site_est", "mail_site_est",
          "profit", "measured_profit", "monthly_proxy", "measured_monthly",
          "capital", "measured_capital", "site_cost_est")


def describe(values):
    if not values:
        return None
    return {
        "n": len(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    annotated = [(row.get("seed"), event) for row in payload["rows"]
                 for event in row.get("events", []) if event.get("phase") == "town"]
    events = [event for _, event in annotated]

    out = {"total": len(events), "families": {}, "seed_year": []}
    for family in ("small", "small_second", "second"):
        rows = [event for event in events if event.get("family") == family]
        candidates = [event for event in rows if event.get("shadow_reject") == "candidate"]
        unique_candidates = {(seed, event.get("town")) for seed, event in annotated
                             if event.get("family") == family
                             and event.get("shadow_reject") == "candidate"}
        record = {
            "n": len(rows),
            "shadow_reject": dict(sorted(Counter(event.get("shadow_reject") for event in rows).items())),
            "candidates": len(candidates),
            "unique_seed_towns": len(unique_candidates),
            "slots_remaining": dict(sorted(Counter(str(event.get("slots_remaining")) for event in candidates).items())),
            "own_airports": dict(sorted(Counter(str(event.get("own_airports")) for event in candidates).items())),
            "competitor_airports": dict(sorted(Counter(str(event.get("competitor_airports")) for event in candidates).items())),
            "profit_ge_50k": sum(event.get("profit", -1) >= 50000 for event in candidates),
            "pax_site_ge_75": sum(event.get("pax_site_est", -1) >= 75 for event in candidates),
            "site_cost_le_30k": sum(event.get("site_cost_est", 30001) <= 30000 for event in candidates),
            "profit_ge_50k_and_pax_site_ge_75": sum(
                event.get("profit", -1) >= 50000 and event.get("pax_site_est", -1) >= 75
                for event in candidates
            ),
            "target_filter_50k_75_30k": sum(
                event.get("profit", -1) >= 50000
                and event.get("pax_site_est", -1) >= 75
                and event.get("site_cost_est", 30001) <= 30000
                for event in candidates
            ),
            "measured_profit_positive": sum(event.get("measured_profit", -1) > 0 for event in candidates),
            "measured_profit_ge_25k": sum(event.get("measured_profit", -1) >= 25000 for event in candidates),
            "measured_profit_ge_50k": sum(event.get("measured_profit", -1) >= 50000 for event in candidates),
            "site_pax_ge_50": sum(event.get("pax_site_est", -1) >= 50 for event in candidates),
            "target_second_measured_50k_site50_cost30": sum(
                event.get("measured_profit", -1) >= 50000
                and event.get("pax_site_est", -1) >= 50
                and event.get("site_cost_est", 30001) <= 30000
                for event in candidates
            ),
            "target_measured_50k_cost30": sum(
                event.get("measured_profit", -1) >= 50000
                and event.get("site_cost_est", 30001) <= 30000
                for event in candidates
            ),
        }
        for field in FIELDS:
            record[field] = describe([
                event[field] for event in candidates
                if isinstance(event.get(field), (int, float)) and event[field] >= 0
            ])
        out["families"][family] = record

    for row in payload["rows"]:
        rows = [event for event in row.get("events", []) if event.get("phase") == "town"]
        if not rows:
            continue
        out["seed_year"].append({
            "seed": row.get("seed"), "year": row.get("year"), "n": len(rows),
            "families": dict(sorted(Counter(event.get("family") for event in rows).items())),
            "shadow_reject": dict(sorted(Counter(event.get("shadow_reject") for event in rows).items())),
        })

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
