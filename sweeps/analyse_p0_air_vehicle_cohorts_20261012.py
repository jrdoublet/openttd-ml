#!/usr/bin/env python3
"""Compare profits of surviving AIR vehicle IDs vs absent at prior December.

This is vehicle-identity cohort analysis, NOT a purchased-on-date log. New
includes replaced, temporarily inactive or reassigned vehicles when missing
from prior December's actively serviced fleet.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def air_vehicles(snapshot):
    if not snapshot.get("ok") or snapshot.get("unresolved_vehicles"):
        raise ValueError("invalid/unresolved telemetry")
    result={}
    for line in snapshot.get("lines",[]):
        if line.get("mode") != "air":continue
        for entry in line.get("vehicle_financials",[]):
            ident=entry.get("vehicle_id")
            profit=entry.get("profit_this_year_gbp")
            if ident is None or not isinstance(profit,(float,int)) or isinstance(profit,bool):
                raise ValueError("bad per-aircraft financial entry")
            if ident in result:
                raise ValueError("duplicate vehicle id in one snapshot")
            result[ident]=float(profit)
    return result


def cohort(current,prior):
    continuing=[v for ident,v in current.items() if ident in prior]
    continuing_prior=[prior[ident] for ident in current if ident in prior]
    newly_observed=[v for ident,v in current.items() if ident not in prior]
    retired_ids=set(prior)-set(current)
    def stats(vals):
        return {"planes":len(vals),"sum_profit_gbp":round(sum(vals),2),
                "mean_profit_gbp_per_plane":round(sum(vals)/len(vals),2) if vals else None,
                "negative_planes":sum(p<0 for p in vals)}
    result = {"continuing":stats(continuing),"not_seen_prior_december":stats(newly_observed),
            "prior_december_not_seen_now":len(retired_ids),"all":stats(list(current.values()))}
    result["continuing_same_ids_prior_year"] = stats(continuing_prior)
    result["continuing_profit_change_same_ids_gbp"] = round(sum(continuing)-sum(continuing_prior),2)
    result["continuing_profit_change_per_plane_gbp"] = round(
        (sum(continuing)-sum(continuing_prior))/len(continuing),2) if continuing else None
    return result


def analyze(c66,seeds=(42,100,999),years=(1972,1973)):
    line=c66.get("line_telemetry")
    if not isinstance(line,dict):raise ValueError("line telemetry unavailable")
    by_key={}
    for item in line.get("snapshots",[]):
        if item.get("seed") not in seeds or item.get("year") not in set(years)|{min(years)-1}:
            continue
        key=(item["seed"],item.get("arm"),item["year"])
        if key in by_key:raise ValueError("duplicate snapshot")
        by_key[key]=air_vehicles(item)
    data={}
    for seed in seeds:
        for arm in ("OpexAI","AAAHogEx"):
            for year in years:
                now=by_key[(seed,arm,year)];before=by_key[(seed,arm,year-1)]
                data[f"{seed}/{arm}/{year}"]=cohort(now,before)
    return {"by_seed_arm_year":data,"limitations":[
        "Only vehicle IDs observed among ACTIVE AIR lines at December checkpoints; may omit aircraft without resolved orders.",
        "The newly-observed category is NOT a purchase cohort; replacements, service changes and missing prior orders are conflated.",
        "Vehicle current-year profits of newly introduced planes cover only their months of service, unlike mature surviving planes.",
        "No causal attribution to fleet resize, demand saturation, operational age or alternate project profitability.",
        "All values come from a single probe-heavy paired C66 bundle, not an uninstrumented control."]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66",type=Path)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    report=analyze(json.loads(a.c66.read_text(encoding="utf8")))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    for seed in (42,100,999):
        for arm in ("OpexAI","AAAHogEx"):
            x=report["by_seed_arm_year"][f"{seed}/{arm}/1973"]
            print(seed,arm,"survivors",x["continuing"],"not_seen_prior",x["not_seen_prior_december"])


if __name__=="__main__": main()
