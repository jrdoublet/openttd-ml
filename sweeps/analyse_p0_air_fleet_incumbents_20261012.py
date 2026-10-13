#!/usr/bin/env python3
"""Do AIR fleet additions coincide with lower incumbent aircraft profit?

Observe SAME station-key service and SAME surviving aircraft ID at December
1972/1973; analyze cohorts on expanded vs unchanged service groups. This is
descriptive association, not causal proof of marginal aircraft dilution.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path


def air_services(snapshot):
    if not snapshot.get("ok") or snapshot.get("unresolved_vehicles"):
        raise ValueError("invalid/unresolved line telemetry")
    services = {}
    for service in snapshot.get("lines", []):
        if service.get("mode") != "air":
            continue
        stations = service.get("station_ids")
        if not isinstance(stations, list) or len(stations) < 2:
            continue
        key = tuple(sorted(stations))
        if key in services:
            raise ValueError("duplicate Opex AIR station-key service")
        vehicles = {}
        for data in service.get("vehicle_financials", []):
            ident, profit = data.get("vehicle_id"), data.get("profit_this_year_gbp")
            if ident is None or not isinstance(profit, (float,int)) or isinstance(profit, bool):
                raise ValueError("invalid vehicle financials")
            if ident in vehicles:
                raise ValueError("duplicated vehicle in same AIR service")
            vehicles[ident] = float(profit)
        services[key] = vehicles
    return services


def pair_services(prior, current):
    paired = []
    for key in sorted(set(prior) & set(current)):
        before, after = prior[key], current[key]
        survivors = set(before) & set(after)
        if not survivors:
            continue
        change = len(after) - len(before)
        category = "expanded" if change > 0 else "contracted" if change < 0 else "unchanged"
        delta = sum(after[ident] - before[ident] for ident in survivors)
        paired.append({"station_ids":list(key),"category":category,"fleet_change":change,
                       "before_vehicles":len(before),"after_vehicles":len(after),
                       "surviving_planes":len(survivors),
                       "incumbent_profit_change_gbp":round(delta,2),
                       "incumbent_profit_change_per_plane_gbp":round(delta/len(survivors),2)})
    aggs = {}
    for category in ("expanded","unchanged","contracted"):
        lines = [item for item in paired if item["category"]==category]
        num = sum(item["surviving_planes"] for item in lines)
        total = sum(item["incumbent_profit_change_gbp"] for item in lines)
        aggs[category] = {"matched_services":len(lines),"surviving_aircraft":num,
                          "total_incumbent_profit_change_gbp":round(total,2),
                          "mean_change_per_survivor_gbp":round(total/num,2) if num else None}
    return {"aggregates":aggs,"paired_services":paired,
            "unpaired_prior":len(set(prior)-set(current)),
            "unpaired_current":len(set(current)-set(prior))}


def analyze(report,seeds=(42,100,999),year=1973):
    telemetry=report.get("line_telemetry")
    if not isinstance(telemetry,dict):
        raise ValueError("line telemetry missing")
    snapshots={}
    for row in telemetry.get("snapshots",[]):
        if row.get("arm")!="OpexAI" or row.get("seed") not in seeds or row.get("year") not in (year-1,year):
            continue
        key=(row["seed"],row["year"])
        if key in snapshots:raise ValueError("duplicate snapshot")
        snapshots[key]=air_services(row)
    return {"by_seed":{str(seed):pair_services(snapshots[(seed,year-1)],snapshots[(seed,year)])
                       for seed in seeds},
            "limitations":[
                "Same station IDs and vehicle IDs across annual December checkpoints; restructured/renumbered stations and temporarily unassigned vehicles are excluded.",
                "A positive aircraft count change between Decembers is only net active fleet growth, NOT an exact purchase count or date.",
                "Profit of surviving aircraft compared within same station-key service removes new-fleet-age dilution, not changes in market demand or external competition.",
                "Association of aircraft growth with incumbent profit changes DOES NOT show adding an aircraft caused the change.",
                "Only three games with intrusive C66 probes and one 1972-to-1973 interval, not a qualification sample."]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66",type=Path)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    report=analyze(json.loads(a.c66.read_text(encoding="utf8")))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    for seed,result in report["by_seed"].items():
        print(seed,result["aggregates"])


if __name__=="__main__":main()
