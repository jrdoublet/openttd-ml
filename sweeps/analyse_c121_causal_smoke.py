#!/usr/bin/env python3
"""Analyse structurelle du smoke causal C121 depuis les checkpoints C66.4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def series(rows, policy):
    return sorted(
        [r for r in rows if (r.get("run") or [None])[0] == "OpexAI" and r.get("duel_policy_id") == policy],
        key=lambda r: r.get("date", ""),
    )


def compact_curve(rows):
    out = []
    previous = None
    keys = (
        "air_airports", "air_primary_vehicles", "air_passenger_capacity",
        "project_builds_sign_total", "air_engine_counts",
    )
    for row in rows:
        state = tuple(json.dumps(row.get(k), sort_keys=True) for k in keys)
        if state == previous and row is not rows[-1]:
            continue
        previous = state
        out.append({
            "date": row.get("date"),
            "cash": row.get("money"),
            "loan": row.get("current_loan"),
            "profit_year": row.get("profit_year"),
            "company_value": row.get("company_value"),
            "airports": row.get("air_airports"),
            "air_fleet": row.get("air_primary_vehicles"),
            "pax_capacity": row.get("air_passenger_capacity"),
            "engine_mix": row.get("air_engine_counts") or {},
            "project_builds": row.get("project_builds_sign_total"),
        })
    return out


def describe(rows):
    if not rows:
        return {"checkpoints": 0, "final": None, "curve": []}
    final = rows[-1]
    return {
        "checkpoints": len(rows),
        "final": {
            "date": final.get("date"),
            "cash": final.get("money"),
            "loan": final.get("current_loan"),
            "profit_year": final.get("profit_year"),
            "company_value": final.get("company_value"),
            "airports": final.get("air_airports"),
            "air_fleet": final.get("air_primary_vehicles"),
            "pax_capacity": final.get("air_passenger_capacity"),
            "engine_mix": final.get("air_engine_counts") or {},
            "project_builds": final.get("project_builds_sign_total"),
            "primary_vehicles": final.get("primary_vehicles"),
        },
        "curve": compact_curve(rows),
    }


def numeric_delta(a, b, key):
    av = (a or {}).get(key)
    bv = (b or {}).get(key)
    if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
        return bv - av
    return None


def summarize_line_telemetry(raw):
    if not isinstance(raw, dict):
        return raw
    out = {k: v for k, v in raw.items() if k != "snapshots"}
    summaries = []
    for snap in raw.get("snapshots") or []:
        if snap.get("arm") != "OpexAI":
            continue
        lines = [line for line in (snap.get("lines") or []) if line.get("mode") == "air"]
        summaries.append({
            "policy": snap.get("duel_policy_id"),
            "date": snap.get("date"),
            "air_lines": len(lines),
            "air_vehicles": sum(int(line.get("vehicles") or 0) for line in lines),
            "line_vehicle_counts": sorted(int(line.get("vehicles") or 0) for line in lines),
            "profit_this_year_gbp": sum(float(line.get("profit_this_year_gbp") or 0) for line in lines),
            "profit_last_year_gbp": sum(float(line.get("profit_last_year_gbp") or 0) for line in lines),
            "negative_lines_this_year": sum(1 for line in lines if float(line.get("profit_this_year_gbp") or 0) < 0),
        })
    out["snapshots"] = summaries
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = load_jsonl(args.jsonl)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    ref = describe(series(rows, "c115_reference"))
    var = describe(series(rows, "c121_causal"))
    rf = ref.get("final") or {}
    vf = var.get("final") or {}
    payload = {
        "campaign_id": result.get("campaign_id"),
        "reference": ref,
        "variant": var,
        "delta_variant_minus_reference": {
            k: numeric_delta(rf, vf, k)
            for k in (
                "profit_year", "company_value", "cash", "loan", "airports",
                "air_fleet", "pax_capacity", "project_builds", "primary_vehicles",
            )
        },
        "policy_comparison": result.get("policy_comparison"),
        "engine_logs": {
            game.get("policy_id"): game.get("engine_log_path")
            for game in result.get("games") or []
        },
        "line_telemetry": summarize_line_telemetry(result.get("line_telemetry")),
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
