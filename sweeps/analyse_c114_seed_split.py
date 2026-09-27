#!/usr/bin/env python3
"""Compare C114 final winners and losers and expose route/equipment signatures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


def mean(values):
    values = [float(v) for v in values if v is not None]
    return statistics.mean(values) if values else None


def final_rows(path: Path):
    latest = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        run = row.get("run") or []
        arm = run[0] if run else row.get("arm")
        seed = run[1] if len(run) > 1 else row.get("seed")
        policy = row.get("duel_policy_id") or row.get("policy_id")
        if arm is None or seed is None or policy is None:
            continue
        key = (str(policy), str(arm), int(seed))
        date = str(row.get("date") or "")
        if key not in latest or date > str(latest[key].get("date") or ""):
            latest[key] = row
    return latest


def engine_share(row, engines=(216, 217)):
    if not row:
        return None
    counts = row.get("air_engine_counts") or {}
    total = sum(int(v or 0) for v in counts.values())
    if total <= 0:
        return None
    wanted = sum(int(counts.get(str(e), counts.get(e, 0)) or 0) for e in engines)
    return 100.0 * wanted / total


def number(row, key):
    if not row:
        return None
    value = row.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path)
    parser.add_argument("jsonl_path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.json_path.read_text(encoding="utf-8"))
    comp = payload.get("policy_comparison") or {}
    ref_policy = str(comp.get("reference_policy_id") or "reference")
    var_policy = str(comp.get("variant_policy_id") or "c114_full_replay")
    latest = final_rows(args.jsonl_path)

    rows = []
    for pair in comp.get("per_pair") or []:
        if not pair.get("complete"):
            continue
        seed = int(pair["seed"])
        metrics = pair.get("metrics") or {}
        structural = pair.get("air_structural_metrics") or {}
        ref = latest.get((ref_policy, "OpexAI", seed))
        var = latest.get((var_policy, "OpexAI", seed))
        py = metrics.get("profit_year") or {}
        cv = metrics.get("company_value") or {}
        perf = metrics.get("performance_history") or {}
        veh = metrics.get("primary_vehicles") or {}
        rating = metrics.get("median_station_rating") or {}
        cv_ref = cv.get("reference_opex")
        cv_delta = cv.get("policy_delta")
        annual = pair.get("annual_trajectory") or []
        rows.append({
            "seed": seed,
            "profit_year_delta": py.get("policy_delta"),
            "profit_year_ref": py.get("reference_opex"),
            "company_value_delta_pct": (100.0 * cv_delta / cv_ref) if cv_ref else None,
            "performance_delta": perf.get("policy_delta"),
            "vehicles_delta": veh.get("policy_delta"),
            "rating_delta": rating.get("policy_delta"),
            "airport_slots_delta": (structural.get("airport_slots_opex") or {}).get("policy_delta"),
            "airport_towns_delta": (structural.get("airport_towns_opex_present") or {}).get("policy_delta"),
            "ref_aircraft": number(ref, "air_primary_vehicles"),
            "var_aircraft": number(var, "air_primary_vehicles"),
            "ref_airports": number(ref, "air_airports"),
            "var_airports": number(var, "air_airports"),
            "ref_pax_capacity": number(ref, "air_passenger_capacity"),
            "var_pax_capacity": number(var, "air_passenger_capacity"),
            "ref_216_217_pct": engine_share(ref),
            "var_216_217_pct": engine_share(var),
            "ref_money": number(ref, "money"),
            "var_money": number(var, "money"),
            "ref_loan": number(ref, "current_loan"),
            "var_loan": number(var, "current_loan"),
            "annual_profit_delta": {str(y.get("year")): y.get("policy_delta") for y in annual},
        })

    groups = {
        "winners": [r for r in rows if (r["profit_year_delta"] or 0) > 0],
        "losers": [r for r in rows if (r["profit_year_delta"] or 0) < 0],
    }
    fields = [
        "profit_year_delta", "profit_year_ref", "company_value_delta_pct", "performance_delta",
        "vehicles_delta", "rating_delta", "airport_slots_delta", "airport_towns_delta",
        "ref_aircraft", "var_aircraft", "ref_airports", "var_airports",
        "ref_pax_capacity", "var_pax_capacity", "ref_216_217_pct", "var_216_217_pct",
        "ref_money", "var_money", "ref_loan", "var_loan",
    ]
    years = sorted({y for r in rows for y in r["annual_profit_delta"]}, key=int)
    summary = {}
    for name, members in groups.items():
        summary[name] = {
            "n": len(members),
            "seeds": [r["seed"] for r in members],
            "means": {field: mean(r[field] for r in members) for field in fields},
            "annual_profit_delta_mean": {year: mean(r["annual_profit_delta"].get(year) for r in members) for year in years},
            "annual_positive_count": {year: sum(1 for r in members if (r["annual_profit_delta"].get(year) or 0) > 0) for year in years},
        }
    print(json.dumps({"groups": summary, "per_seed": sorted(rows, key=lambda r: r["profit_year_delta"] or 0)}, indent=2))


if __name__ == "__main__":
    main()
