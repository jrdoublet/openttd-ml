#!/usr/bin/env python3
"""Financial attribution of ACTIVE vehicle services, not the company accounts.

Use only paired same-game Opex/AAA December savegame line telemetry. The
sum of vehicle's year-to-date profit is NOT equivalent to company profit_year,
which may use a different accounting interval and other incomes/expenses.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def summarize(snapshot):
    if not snapshot.get("ok") or snapshot.get("unresolved_vehicles"):
        raise ValueError("unresolved or invalid active-service snapshot")
    by_mode = defaultdict(lambda: {"services": 0, "primary_vehicles": 0,
                                   "vehicle_profit_this_year_gbp": 0.0,
                                   "vehicle_profit_last_year_gbp": 0.0})
    seen = set()
    for line in snapshot.get("lines", []):
        mode = line.get("mode", "unknown")
        vehicles = line.get("vehicle_ids", [])
        if not isinstance(vehicles, list):
            raise ValueError("missing vehicle ids")
        for vehicle in vehicles:
            if vehicle in seen:
                raise ValueError(f"duplicate primary vehicle id within snapshot: {vehicle}")
            seen.add(vehicle)
        out = by_mode[mode]
        out["services"] += 1
        out["primary_vehicles"] += len(vehicles)
        for fld in ("profit_this_year_gbp", "profit_last_year_gbp"):
            value = line.get(fld)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"missing numerical {fld}")
            out[f"vehicle_{fld}"] += float(value)
    return {k: {key: round(v, 2) if isinstance(v, float) else v for key, v in item.items()}
            for k, item in sorted(by_mode.items())}


def analyze(report, seeds=(42,100,999), years=(1971,1972,1973)):
    line = report.get("line_telemetry")
    if not isinstance(line, dict):
        raise ValueError("line telemetry not collected")
    grouped = defaultdict(dict)
    for row in line.get("snapshots", []):
        if row.get("seed") not in seeds or row.get("year") not in years or row.get("repeat") != 0:
            continue
        key = (row["seed"], row["year"])
        arm = row.get("arm")
        if arm in grouped[key]:
            raise ValueError(f"duplicate snapshot {key} {arm}")
        grouped[key][arm] = summarize(row)
    data = {}
    for seed in seeds:
        for year in years:
            pair = grouped[(seed,year)]
            if set(pair) != {"OpexAI","AAAHogEx"}:
                raise ValueError(f"missing paired company services {seed}/{year}")
            a,b = pair["OpexAI"],pair["AAAHogEx"]
            differences = {}
            for mode in sorted(set(a)|set(b)):
                left = a.get(mode,{})
                right = b.get(mode,{})
                differences[mode] = {k:round(left.get(k,0)-right.get(k,0),2)
                    for k in ("services","primary_vehicles","vehicle_profit_this_year_gbp","vehicle_profit_last_year_gbp")}
            data[f"{seed}/{year}"] = {"opex":a,"aaa":b,"opex_minus_aaa":differences}
    return {"by_seed_year":data,"limitations":[
        "Only ACTIVE services with primary vehicles and resolved orders are represented; idle or unvehicled lines are absent.",
        "A vehicle can appear in only one service in a snapshot; uniqueness enforced.",
        "Vehicle profit_this_year_gbp is year-to-date from December savegame, not trailing-four-quarters company profit_year.",
        "Mode attribution helps describe composition, but not marginal ROI or true counterfactual constructibility.",
        "The paired campaign is heavily instrumented and economically nonneutral relative to the uninstrumented baseline."]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66", type=Path)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    d=analyze(json.loads(args.c66.read_text(encoding="utf8")))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    for case,row in d["by_seed_year"].items():
        if case.endswith("/1973"):
            print(case,{mode:stats["vehicle_profit_this_year_gbp"] for mode,stats in row["opex_minus_aaa"].items()})


if __name__=="__main__":
    main()
