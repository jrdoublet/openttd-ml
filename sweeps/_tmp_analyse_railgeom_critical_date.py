import json
import statistics
from collections import Counter
from pathlib import Path


src = Path("results/railgeom_guard_diag_40x5_20261004.jsonl")
rec = {}
for line in src.open(encoding="utf-8"):
    try:
        d = json.loads(line)
    except Exception:
        continue
    policy = d.get("duel_policy_id")
    ai = d.get("policy_id")
    run = d.get("run") or []
    if policy not in ("reference", "rail_geometry_guard") or len(run) < 2:
        continue
    seed = run[1]
    date = d.get("date")
    if not date:
        continue
    rec[(policy, ai, seed, date)] = d

seeds = sorted({k[2] for k in rec if k[0] == "reference" and k[1] == "reference"})
dates = sorted({k[3] for k in rec if k[0] == "reference" and k[1] == "reference"})

rows = []
first_divergence = {}
first_profit_divergence = {}
first_rail_station_divergence = {}
first_rail_vehicle_divergence = {}
for date in dates:
    profit_deltas = []
    cv_deltas = []
    rail_station_deltas = []
    rail_vehicle_deltas = []
    gap_deltas = []
    for seed in seeds:
        reference = rec.get(("reference", "reference", seed, date))
        variant = rec.get(("rail_geometry_guard", "rail_geometry_guard", seed, date))
        ref_aaa = rec.get(("reference", "AAAHogEx", seed, date))
        var_aaa = rec.get(("rail_geometry_guard", "AAAHogEx", seed, date))
        if not reference or not variant:
            continue

        profit_delta = (variant.get("profit_year") or 0) - (reference.get("profit_year") or 0)
        cv_delta = (variant.get("company_value") or 0) - (reference.get("company_value") or 0)
        ref_rail_stations = (reference.get("stations_by_facility") or {}).get("rail", 0)
        var_rail_stations = (variant.get("stations_by_facility") or {}).get("rail", 0)
        rail_station_delta = var_rail_stations - ref_rail_stations
        ref_rail_vehicles = (reference.get("primary_vehicles_by_mode") or {}).get("rail", 0)
        var_rail_vehicles = (variant.get("primary_vehicles_by_mode") or {}).get("rail", 0)
        rail_vehicle_delta = var_rail_vehicles - ref_rail_vehicles

        profit_deltas.append(profit_delta)
        cv_deltas.append(cv_delta)
        rail_station_deltas.append(rail_station_delta)
        rail_vehicle_deltas.append(rail_vehicle_delta)

        if ref_aaa and var_aaa:
            ref_gap = (reference.get("profit_year") or 0) - (ref_aaa.get("profit_year") or 0)
            var_gap = (variant.get("profit_year") or 0) - (var_aaa.get("profit_year") or 0)
            gap_deltas.append(var_gap - ref_gap)

        if seed not in first_divergence and (
            profit_delta != 0
            or cv_delta != 0
            or rail_station_delta != 0
            or rail_vehicle_delta != 0
        ):
            first_divergence[seed] = date
        if seed not in first_profit_divergence and profit_delta != 0:
            first_profit_divergence[seed] = date
        if seed not in first_rail_station_divergence and rail_station_delta != 0:
            first_rail_station_divergence[seed] = date
        if seed not in first_rail_vehicle_divergence and rail_vehicle_delta != 0:
            first_rail_vehicle_divergence[seed] = date

    if profit_deltas:
        rows.append(
            {
                "date": date,
                "n": len(profit_deltas),
                "profit_mean": sum(profit_deltas) / len(profit_deltas),
                "profit_median": statistics.median(profit_deltas),
                "wins": sum(x > 0 for x in profit_deltas),
                "losses": sum(x < 0 for x in profit_deltas),
                "ties": sum(x == 0 for x in profit_deltas),
                "cv_mean": sum(cv_deltas) / len(cv_deltas),
                "rail_stations_mean": sum(rail_station_deltas) / len(rail_station_deltas),
                "rail_station_nonzero": sum(x != 0 for x in rail_station_deltas),
                "rail_vehicles_mean": sum(rail_vehicle_deltas) / len(rail_vehicle_deltas),
                "gap_mean": sum(gap_deltas) / len(gap_deltas) if gap_deltas else None,
            }
        )

print("SEEDS", len(seeds), "DATES", len(dates))
print("FIRST_DIVERGENCE_COUNTS")
for date, count in sorted(Counter(first_divergence.values()).items()):
    print(date, count)
print("FIRST_DIVERGED_TOTAL", len(first_divergence))
print("FIRST_PROFIT_DIVERGENCE_COUNTS")
for date, count in sorted(Counter(first_profit_divergence.values()).items()):
    print(date, count)
print("FIRST_RAIL_STATION_DIVERGENCE_COUNTS")
for date, count in sorted(Counter(first_rail_station_divergence.values()).items()):
    print(date, count)
print("FIRST_RAIL_VEHICLE_DIVERGENCE_COUNTS")
for date, count in sorted(Counter(first_rail_vehicle_divergence.values()).items()):
    print(date, count)

print("YEAR_ENDS")
for row in rows:
    if row["date"].endswith("-12-01"):
        print(json.dumps(row, ensure_ascii=False))

print("KEY_MONTHS")
for row in rows:
    if row["date"] >= "1971-01-01" and (
        row["ties"] <= 30
        or abs(row["profit_mean"]) >= 10000
        or row["rail_station_nonzero"] >= 5
    ):
        print(json.dumps(row, ensure_ascii=False))

Path("results/railgeom_guard_critical_date_40x5_20261004.json").write_text(
    json.dumps(
        {
            "first_divergence": first_divergence,
            "first_profit_divergence": first_profit_divergence,
            "first_rail_station_divergence": first_rail_station_divergence,
            "first_rail_vehicle_divergence": first_rail_vehicle_divergence,
            "monthly": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
