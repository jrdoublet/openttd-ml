#!/usr/bin/env python3
"""Join existing P0 decisions, outcomes and uninstrumented paired physical snapshots.

Do not merge the *trajectories* of profiled P2/P5 games with uninstrumented
economic C66 games. The join is seed/year only, for competing hypotheses.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path


SEEDS = (42, 100, 999, 1234, 5678)
YEARS = (1970, 1971, 1972, 1973)
MODES = ("air", "rail")


def valid_rows(rows, seeds=SEEDS):
    selected = defaultdict(dict)
    for row in rows:
        run = row.get("run", [])
        if (not isinstance(run, list) or len(run) != 3 or run[0] not in
                ("OpexAI", "AAAHogEx") or run[1] not in seeds or run[2] != 0):
            continue
        date = row.get("date", "")
        if len(date) != 10 or date[:4] not in {str(y) for y in YEARS}:
            continue
        key = (int(run[1]), run[0])
        if date in selected[key]:
            raise ValueError(f"duplicate checkpoint {key} {date}")
        selected[key][date] = row
    for seed in seeds:
        for arm in ("OpexAI", "AAAHogEx"):
            for year in YEARS:
                date = f"{year}-12-01"
                if date not in selected[(seed, arm)]:
                    raise ValueError(f"missing {seed} {arm} {date}")
    return selected


def physical(row):
    if not row.get("vehs_chunk_valid") or not row.get("stnn_chunk_valid"):
        raise ValueError("invalid physical counters")
    vehicles = row.get("primary_vehicles_by_mode")
    facilities = row.get("stations_by_facility")
    if not isinstance(vehicles, dict) or not isinstance(facilities, dict):
        raise ValueError("missing mode physical counters")
    return {"profit_year": row.get("profit_year"),
            "value": row.get("company_value"),
            "air_vehicles": vehicles.get("air"),
            "rail_vehicles": vehicles.get("rail"),
            "airports": facilities.get("airport"),
            "rail_stations": facilities.get("rail"),
            "stations": row.get("n_stations"),
            "vehicles": row.get("primary_vehicles")}


def paired_economy(checkpoints, seed, year):
    date = f"{year}-12-01"
    opex = physical(checkpoints[(seed, "OpexAI")][date])
    aaa = physical(checkpoints[(seed, "AAAHogEx")][date])
    deltas = {k: opex[k] - aaa[k] if isinstance(opex[k], (int, float))
              and isinstance(aaa[k], (int, float)) else None for k in opex}
    return {"date": date, "opex": opex, "aaa": aaa, "opex_minus_aaa": deltas}


def first_negative_gap(checkpoints, seed, metric, start="1971-01-01"):
    opex = checkpoints[(seed, "OpexAI")]
    aaa = checkpoints[(seed, "AAAHogEx")]
    for date in sorted(set(opex) & set(aaa)):
        if date < start:
            continue
        if metric == "profit_year" and (
            opex[date].get("profit_year_coverage") != "complete" or
            aaa[date].get("profit_year_coverage") != "complete" or
            opex[date].get("profit_year_quarters_valid") != 4 or
            aaa[date].get("profit_year_quarters_valid") != 4
        ):
            continue
        try:
            left, right = physical(opex[date])[metric], physical(aaa[date])[metric]
        except ValueError:
            continue
        if isinstance(left, (float, int)) and isinstance(right, (float, int)) and left < right:
            return date
    return None


def join(checkpoints, p2, p5, seeds=SEEDS):
    result = {}
    for seed in seeds:
        yearly = {}
        for year in YEARS:
            key = str(year)
            admission = p2["by_seed"][str(seed)][key]
            builds = p5["by_seed"][str(seed)][key]
            cost = paired_economy(checkpoints, seed, year)
            yearly[key] = {
                "unprofiled_paired_economy": cost,
                "profiled_admission_after_dispatch": {
                    k: admission.get(k) for k in ("passes", "start_empty", "start_nonempty_no_build",
                                                  "passes_built", "units_built", "rail_pool_nonempty_after",
                                                  "rail_fundable_after", "rail_constructed")},
                "profiled_net_new_line_events": builds["lines_by_mode"],
                "profiled_paid_astar_calls": builds["search_paid_calls"],
                "profiled_astar_window_ops": builds["search_window_ops"],
                "profiled_astar_wait_days": builds["search_days"],
                "profiled_monthly_admissions": admission["months"],
                "profiled_monthly_line_events": builds["lines_by_month"],
            }
        result[str(seed)] = {
            "by_year": yearly,
            "first_observed_negative_gap_month_from_1971": {
                metric: first_negative_gap(checkpoints, seed, metric)
                for metric in ("profit_year", "value", "air_vehicles", "airports",
                               "rail_vehicles", "rail_stations")},
        }
    return {
        "seeds": list(seeds), "by_seed": result,
        "limitations": [
            "P2/P5 logs are from a profiled campaign and MUST NOT be causally joined to the unprofiled C66 economic trajectory.",
            "first_negative_gap_month means earliest valid paired checkpoint where OpexAI < AAA, not first divergent AI decision. Profit requires 4 valid quarters on both arms.",
            "P2 rail affordability is measured after dispatch and does not prove construction feasibility when admitted.",
            "P5 line events measure positive NET changes to _lines, not gross builds, survival or profitability.",
            "Rail/AIR active services and complete construction failures cannot be reconstructed from the annual C66 stocks.",
            "Projects build_ops measures waiting and NoAI commands, not raw Squirrel VM instructions.",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-jsonl", type=Path, required=True)
    ap.add_argument("--p2", type=Path, required=True)
    ap.add_argument("--p5", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with args.baseline_jsonl.open(encoding="utf8") as handle:
        checkpoints = valid_rows(json.loads(s) for s in handle if s.strip())
    result = join(checkpoints, json.loads(args.p2.read_text(encoding="utf8")),
                  json.loads(args.p5.read_text(encoding="utf8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    for seed, data in result["by_seed"].items():
        print(seed, data["first_observed_negative_gap_month_from_1971"])
        for year in ("1971", "1972", "1973"):
            row = data["by_year"][year]
            print(" ", year, "gap_profit", row["unprofiled_paired_economy"]["opex_minus_aaa"]["profit_year"],
                  "P2", row["profiled_admission_after_dispatch"]["passes"],
                  "empty", row["profiled_admission_after_dispatch"]["start_empty"],
                  "lines", row["profiled_net_new_line_events"])


if __name__ == "__main__":
    main()
