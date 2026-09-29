#!/usr/bin/env python3
"""Analyse appariee C120 5x6 : couverture administrative + economie."""

from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "results" / "diag_c120_territorial_5x6_20260928.jsonl"
RESULT = ROOT / "results" / "diag_c120_territorial_5x6_20260928.json"
LEVELS = (4, 6, 10, 15, 20, 23)


def month_index(date: str) -> int:
    year, month, _day = map(int, date.split("-"))
    return year * 12 + month


def rows_for(rows, seed, policy):
    return sorted(
        (
            row for row in rows
            if (row.get("run") or [None, None])[0] == "OpexAI"
            and (row.get("run") or [None, None])[1] == seed
            and row.get("duel_policy_id") == policy
        ),
        key=lambda row: row["date"],
    )


def milestone(rows, level):
    hit = next((row for row in rows if int(row.get("airport_towns_opex_present") or 0) >= level), None)
    return hit["date"] if hit else None


def summarize_arm(rows):
    final = rows[-1]
    return {
        "final_date": final["date"],
        "airports": int(final.get("air_airports") or 0),
        "towns": int(final.get("airport_towns_opex_present") or 0),
        "aaahogex_towns": int(final.get("airport_towns_aaahogex_present") or 0),
        "air_fleet": int(final.get("air_primary_vehicles") or 0),
        "pax_capacity": int(final.get("air_passenger_capacity") or 0),
        "profit_year": final.get("profit_year"),
        "company_value": final.get("company_value"),
        "milestones": {str(level): milestone(rows, level) for level in LEVELS},
    }


def main():
    rows = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    seeds = sorted({
        int((row.get("run") or [None, None])[1])
        for row in rows
        if (row.get("run") or [None])[0] == "OpexAI"
    })

    pairs = []
    for seed in seeds:
        ref_rows = rows_for(rows, seed, "reference")
        var_rows = rows_for(rows, seed, "c120_territorial")
        if not ref_rows or not var_rows:
            continue
        ref = summarize_arm(ref_rows)
        var = summarize_arm(var_rows)
        milestone_delta = {}
        for level in LEVELS:
            r = ref["milestones"][str(level)]
            v = var["milestones"][str(level)]
            milestone_delta[str(level)] = None if r is None or v is None else month_index(v) - month_index(r)
        pairs.append({
            "seed": seed,
            "reference": ref,
            "variant": var,
            "delta": {
                "towns": var["towns"] - ref["towns"],
                "airports": var["airports"] - ref["airports"],
                "air_fleet": var["air_fleet"] - ref["air_fleet"],
                "pax_capacity": var["pax_capacity"] - ref["pax_capacity"],
                "profit_year": var["profit_year"] - ref["profit_year"],
                "company_value": var["company_value"] - ref["company_value"],
                "milestone_months": milestone_delta,
            },
        })

    aggregate = {}
    for level in LEVELS:
        values = [p["delta"]["milestone_months"][str(level)] for p in pairs
                  if p["delta"]["milestone_months"][str(level)] is not None]
        aggregate[str(level)] = {
            "comparable": len(values),
            "earlier": sum(v < 0 for v in values),
            "same": sum(v == 0 for v in values),
            "later": sum(v > 0 for v in values),
            "mean_delta_months": statistics.mean(values) if values else None,
            "median_delta_months": statistics.median(values) if values else None,
        }

    payload = {
        "campaign_id": result.get("campaign_id"),
        "pairs": pairs,
        "aggregate": {
            "milestones": aggregate,
            "final_towns_delta_mean": statistics.mean(p["delta"]["towns"] for p in pairs),
            "final_towns_delta_median": statistics.median(p["delta"]["towns"] for p in pairs),
            "final_airports_delta_mean": statistics.mean(p["delta"]["airports"] for p in pairs),
            "final_air_fleet_delta_mean": statistics.mean(p["delta"]["air_fleet"] for p in pairs),
            "final_pax_capacity_delta_mean": statistics.mean(p["delta"]["pax_capacity"] for p in pairs),
            "profit_year_delta_mean": statistics.mean(p["delta"]["profit_year"] for p in pairs),
            "profit_year_delta_median": statistics.median(p["delta"]["profit_year"] for p in pairs),
            "company_value_delta_mean": statistics.mean(p["delta"]["company_value"] for p in pairs),
            "town_wins": sum(p["delta"]["towns"] > 0 for p in pairs),
            "town_ties": sum(p["delta"]["towns"] == 0 for p in pairs),
            "town_losses": sum(p["delta"]["towns"] < 0 for p in pairs),
        },
    }
    out = ROOT / "results" / "diag_c120_territorial_5x6_20260928_analysis.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["aggregate"], indent=2, sort_keys=True))
    for pair in pairs:
        print(
            pair["seed"],
            "towns", pair["reference"]["towns"], "->", pair["variant"]["towns"],
            "airports", pair["reference"]["airports"], "->", pair["variant"]["airports"],
            "dPY", pair["delta"]["profit_year"],
            "dCV", pair["delta"]["company_value"],
            "milestones", pair["delta"]["milestone_months"],
        )


if __name__ == "__main__":
    main()
