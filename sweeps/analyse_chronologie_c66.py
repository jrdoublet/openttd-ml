"""Chronologie descriptive d'un duel C66.3 figé, depuis ses checkpoints mensuels.

Usage: python sweeps/analyse_chronologie_c66.py results/<campagne>.json
Ne qualifie aucun changement de politique et n'invente pas les données manquantes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import statistics


ARMS = ("OpexAI", "AAAHogEx")
SCALARS = (
    "profit_year", "company_value", "money", "n_vehicles", "n_stations",
    "air_primary_vehicles", "air_airports", "performance_history",
    "median_station_rating", "air_passenger_capacity",
    "airport_slots_opex", "airport_slots_aaahogex",
    "airport_towns_opex_present", "airport_towns_aaahogex_present",
)
MODES = ("air", "rail", "road", "water")


def mean(rows, field):
    vals = [row.get(field) for row in rows]
    if not vals or any(not isinstance(v, (int, float)) for v in vals):
        return None
    return round(statistics.mean(vals), 3)


def series_mean(rows, field, names):
    details = [row.get(field) for row in rows]
    if not details or any(not isinstance(v, dict) for v in details):
        return {name: None for name in names}
    return {name: round(statistics.mean(float(v.get(name, 0)) for v in details), 3)
            for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    checkpoint = args.report.with_suffix(".jsonl")
    years = [1970 + index for index in range(report["years"])]
    seeds = list(report["seeds"])
    rows = {}
    for line in checkpoint.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("duel_policy_id") != report["policy_id"]:
            continue
        arm, seed, repeat = record["run"]
        if repeat != 0 or arm not in ARMS:
            continue
        key = (record["date"], seed, arm)
        if key in rows:
            raise ValueError(f"duplicate checkpoint: {key}")
        rows[key] = record

    snapshots = defaultdict(list)
    snapshot_keys = set()
    telemetry = report.get("line_telemetry") or {}
    for snap in telemetry.get("snapshots", []):
        if snap.get("duel_policy_id") == report["policy_id"] and snap.get("repeat", 0) == 0:
            unique = (snap.get("date"), snap.get("arm"), snap.get("seed"))
            if unique in snapshot_keys:
                raise ValueError(f"duplicate line snapshot: {unique}")
            snapshot_keys.add(unique)
            snapshots[(snap.get("date"), snap.get("arm"))].append(snap)

    output = {"campaign_id": report.get("campaign_id"), "manifest_sha256": report.get("manifest_sha256"),
              "source_bundle_sha256": report.get("source_bundle_sha256"),
              "seeds": seeds, "years": years, "annual": [], "per_seed": [], "warnings": [],
              "method": "December 1 savegames, rolling profit of last up to 4 closed quarters; first year partial"}
    if report.get("failed_runs"):
        output["warnings"].append(f"failed runs: {len(report['failed_runs'])}")
    if len(report.get("games") or []) != len(seeds):
        output["warnings"].append("number of completed games differs from seeds")

    for year in years:
        date = f"{year}-12-01"
        arms = {arm: [rows[(date, seed, arm)] for seed in seeds
                      if (date, seed, arm) in rows] for arm in ARMS}
        year_record = {"year": year, "checkpoint": date, "n_seeds": len(seeds), "arms": {}, "paired": {}}
        for arm, entries in arms.items():
            if len(entries) != len(seeds):
                output["warnings"].append(f"{year} {arm}: {len(entries)}/{len(seeds)} checkpoints")
            record = {"n": len(entries), "metrics": {metric: mean(entries, metric) for metric in SCALARS},
                      "vehicles_by_mode": series_mean(entries, "primary_vehicles_by_mode", MODES),
                      "stations_by_facility": series_mean(entries, "stations_by_facility",
                          ("airport", "rail", "bus", "truck", "dock")),
                      "profit_coverage": dict(Counter(entry.get("profit_year_coverage") for entry in entries))}
            lines = snapshots.get((date, arm), [])
            if lines:
                if len(lines) != len(seeds) or any(s.get("ok") is not True for s in lines):
                    output["warnings"].append(f"{year} {arm}: partial or invalid line telemetry")
                record["lines"] = {"n_snapshots": len(lines),
                                   "n_ok": sum(s.get("ok") is True for s in lines),
                                   "by_mode": {}}
                for mode in MODES:
                    if len(lines) == len(seeds) and all(s.get("ok") is True for s in lines):
                        sums = [([x for x in s.get("lines", []) if x.get("mode") == mode]) for s in lines]
                        record["lines"]["by_mode"][mode] = {
                            "mean_services": round(statistics.mean(len(item) for item in sums), 3),
                            "mean_vehicles": round(statistics.mean(sum(x.get("vehicles", 0) for x in item) for item in sums), 3),
                            "mean_vehicle_profit_ytd": round(statistics.mean(sum(x.get("profit_this_year_gbp", 0) for x in item) for item in sums), 3),
                        }
            year_record["arms"][arm] = record

        matches = [(seed, rows[(date, seed, "OpexAI")], rows[(date, seed, "AAAHogEx")])
                   for seed in seeds if (date, seed, "OpexAI") in rows
                   and (date, seed, "AAAHogEx") in rows]
        for metric in ("profit_year", "company_value", "air_airports", "n_vehicles", "n_stations"):
            pairs = [(seed, op[metric] - aa[metric]) for seed, op, aa in matches
                     if isinstance(op.get(metric), (int, float))
                     and isinstance(aa.get(metric), (int, float))]
            year_record["paired"][metric] = {
                "n": len(pairs), "mean_delta": round(statistics.mean(x[1] for x in pairs), 3) if pairs else None,
                "median_delta": round(statistics.median(x[1] for x in pairs), 3) if pairs else None,
                "wins": sum(x[1] > 0 for x in pairs), "losses": sum(x[1] < 0 for x in pairs),
                "ties": sum(x[1] == 0 for x in pairs),
            }
        for seed, op, aa in matches:
            output["per_seed"].append({"year": year, "seed": seed,
                "opex_profit": op.get("profit_year"), "aaa_profit": aa.get("profit_year"),
                "opex_value": op.get("company_value"), "aaa_value": aa.get("company_value"),
                "opex_airports": op.get("air_airports"), "aaa_airports": aa.get("air_airports"),
                "opex_vehicles_by_mode": op.get("primary_vehicles_by_mode"),
                "aaa_vehicles_by_mode": aa.get("primary_vehicles_by_mode")})
        output["annual"].append(year_record)

    analysis = args.report.with_suffix(".analysis.json")
    analysis.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path = args.report.with_suffix(".annual.csv")
    with csv_path.open("w", encoding="utf-8", newline="") as dest:
        writer = csv.writer(dest)
        writer.writerow(["year", "opex_profit", "aaa_profit", "delta_profit", "opex_value", "aaa_value",
                         "opex_airports", "aaa_airports", "opex_trains", "aaa_trains", "opex_road", "aaa_road",
                         "opex_aircraft", "aaa_aircraft", "opex_stations", "aaa_stations", "paired_wins", "n"])
        for row in output["annual"]:
            o, a = [row["arms"][arm] for arm in ARMS]
            om, am = o["metrics"], a["metrics"]
            writer.writerow([row["year"], om["profit_year"], am["profit_year"],
                             row["paired"]["profit_year"]["mean_delta"], om["company_value"], am["company_value"],
                             om["air_airports"], am["air_airports"], o["vehicles_by_mode"]["rail"],
                             a["vehicles_by_mode"]["rail"], o["vehicles_by_mode"]["road"],
                             a["vehicles_by_mode"]["road"], o["vehicles_by_mode"]["air"],
                             a["vehicles_by_mode"]["air"], om["n_stations"], am["n_stations"],
                             row["paired"]["profit_year"]["wins"], row["paired"]["profit_year"]["n"]])
    print(f"analysis={analysis} annual_csv={csv_path}")
    print(f"years={years} games={len(report.get('games') or [])} warnings={output['warnings']}")


if __name__ == "__main__":
    main()
