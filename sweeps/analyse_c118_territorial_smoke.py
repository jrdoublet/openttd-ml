#!/usr/bin/env python3
"""Analyse C118 depuis les checkpoints mensuels C66.4 déjà produits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "results" / "smoke_c118_territorial_1x3_20260927_r2.jsonl"
DEFAULT_RESULT = ROOT / "results" / "smoke_c118_territorial_1x3_20260927_r2.json"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def series(rows, policy):
    return sorted([r for r in rows if (r.get("run") or [None])[0] == "OpexAI" and r.get("duel_policy_id") == policy], key=lambda r: r.get("date", ""))


def thresholds(rows, field):
    out, previous = [], 0
    for row in rows:
        value = int(row.get(field) or 0)
        if value > previous:
            out.extend({"n": level, "observed_by": row["date"]} for level in range(previous + 1, value + 1))
            previous = value
    return out


def annual(rows):
    by_year = {int(str(row["date"])[:4]): row for row in rows}
    return [{"year": year, "date": row["date"], "airports": row.get("air_airports"), "covered_towns": row.get("airport_towns_opex_present"), "air_fleet": row.get("air_primary_vehicles"), "pax_capacity": row.get("air_passenger_capacity"), "engine_mix": row.get("air_engine_counts") or {}, "profit_year": row.get("profit_year"), "company_value": row.get("company_value")} for year, row in sorted(by_year.items())]


def describe(rows):
    final = rows[-1]
    return {"monthly_checkpoints": len(rows), "annual": annual(rows), "airport_thresholds": thresholds(rows, "air_airports"), "town_thresholds": thresholds(rows, "airport_towns_opex_present"), "final": {"date": final["date"], "airports": final.get("air_airports"), "covered_towns": final.get("airport_towns_opex_present"), "air_fleet": final.get("air_primary_vehicles"), "pax_capacity": final.get("air_passenger_capacity"), "engine_mix": final.get("air_engine_counts") or {}, "project_builds_sign_total": final.get("project_builds_sign_total"), "project_builds_sign_by_year": final.get("project_builds_sign_by_year") or {}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    rows = load_jsonl(args.jsonl)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    reference, variant = series(rows, "reference"), series(rows, "c118_territorial")
    if not reference or not variant:
        raise RuntimeError("checkpoints C118 incomplets")
    pair = ((result.get("policy_comparison") or {}).get("per_pair") or [{}])[0]
    payload = {"campaign_id": result.get("campaign_id"), "checkpoint_resolution": "monthly; observed_by is an upper bound inside the preceding month", "reference": describe(reference), "variant": describe(variant), "economic_metrics": pair.get("metrics") or {}, "air_structural_metrics": pair.get("air_structural_metrics") or {}, "decision": {"run_5x6": False, "reason": "coverage slower in 1970-1971 and economics severely worse"}}
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
