#!/usr/bin/env python3
"""Analyse C120 depuis les checkpoints mensuels C66.4 et les panneaux C0*."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "results" / "smoke_c120_territorial_1x3_20260928_r8.jsonl"
DEFAULT_RESULT = ROOT / "results" / "smoke_c120_territorial_1x3_20260928_r8.json"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def series(rows, policy):
    return sorted(
        [
            r for r in rows
            if (r.get("run") or [None])[0] == "OpexAI"
            and r.get("duel_policy_id") == policy
        ],
        key=lambda r: r.get("date", ""),
    )


def milestone_dates(rows, field, levels=(4, 6, 10, 15, 20, 23)):
    result = {}
    for level in levels:
        hit = next((row for row in rows if int(row.get(field) or 0) >= level), None)
        result[str(level)] = hit.get("date") if hit else None
    return result


def coverage_event_date(event):
    return f"{int(event['year']):04d}-{int(event['month']):02d}-{int(event['day']):02d}"


def real_town_milestones(rows, levels=(4, 6, 10, 15, 20, 23)):
    events = (rows[-1].get("c118_coverage_events") or []) if rows else []
    result = {}
    for level in levels:
        hit = next((event for event in events if int(event.get("towns") or 0) >= level), None)
        result[str(level)] = coverage_event_date(hit) if hit else None
    return result


def monthly(rows):
    out = []
    for row in rows:
        events = row.get("c118_coverage_events") or []
        real_covered = int(events[-1].get("towns") or 0) if events else 0
        out.append({
            "date": row.get("date"),
            "cash": row.get("money"),
            "loan": row.get("current_loan"),
            "airports": row.get("air_airports"),
            "covered_towns": real_covered,
            "airport_towns_present": row.get("airport_towns_opex_present"),
            "air_fleet": row.get("air_primary_vehicles"),
            "pax_capacity": row.get("air_passenger_capacity"),
            "engine_mix": row.get("air_engine_counts") or {},
            "project_builds": row.get("project_builds_sign_total"),
            "c120_decisions": row.get("c120_decisions") or [],
        })
    return out


def describe(rows):
    final = rows[-1]
    final_events = final.get("c118_coverage_events") or []
    final_real_covered = int(final_events[-1].get("towns") or 0) if final_events else 0
    return {
        "monthly_checkpoints": len(rows),
        "airport_milestones": milestone_dates(rows, "air_airports"),
        "town_milestones": real_town_milestones(rows),
        "airport_town_presence_milestones": milestone_dates(rows, "airport_towns_opex_present"),
        "monthly": monthly(rows),
        "final": {
            "date": final.get("date"),
            "airports": final.get("air_airports"),
            "covered_towns": final_real_covered,
            "airport_towns_present": final.get("airport_towns_opex_present"),
            "air_fleet": final.get("air_primary_vehicles"),
            "pax_capacity": final.get("air_passenger_capacity"),
            "engine_mix": final.get("air_engine_counts") or {},
            "profit_year": final.get("profit_year"),
            "company_value": final.get("company_value"),
            "c120_decision_count": final.get("c120_decision_count"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = load_jsonl(args.jsonl)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    reference = series(rows, "reference")
    variant = series(rows, "c120_territorial")
    if not reference or not variant:
        raise RuntimeError("checkpoints C120 incomplets")
    pair = ((result.get("policy_comparison") or {}).get("per_pair") or [{}])[0]
    payload = {
        "campaign_id": result.get("campaign_id"),
        "checkpoint_resolution": "monthly; milestone date is an observed-by upper bound",
        "reference": describe(reference),
        "variant": describe(variant),
        "economic_metrics": pair.get("metrics") or {},
        "air_structural_metrics": pair.get("air_structural_metrics") or {},
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
