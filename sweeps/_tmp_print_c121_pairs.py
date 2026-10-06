#!/usr/bin/env python3
import json


path = "results/c121_current_5x6_jr5_20260929.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

pc = data.get("policy_comparison", {})
print("policy_comparison keys:", sorted(pc.keys()))
for pair in pc.get("per_pair", []):
    m = pair.get("metrics", {})
    s = pair.get("air_structural_metrics", {})
    print("PAIR", pair.get("seed"),
          "py", m.get("profit_year", {}).get("policy_delta"),
          "cv", m.get("company_value", {}).get("policy_delta"),
          "veh", m.get("primary_vehicles", {}).get("policy_delta"),
          "slots", s.get("airport_slots_opex", {}).get("policy_delta"),
          "towns", s.get("airport_towns_opex_present", {}).get("policy_delta"))
print("TOP", sorted(data.keys()))
for key in ("games", "policy_reports"):
    if key in data:
        value = data[key]
        print("RUNKEY", key, type(value).__name__, len(value))
        seq = value.values() if isinstance(value, dict) else value
        for run in seq:
            if isinstance(run, dict) and run.get("seed") in (42, 1234):
                print("RUN", key, run.get("seed"), run.get("policy_id"), "keys", sorted(run.keys()))
                companies = run.get("companies", [])
                company_seq = companies.values() if isinstance(companies, dict) else companies
                for company in company_seq:
                    if not isinstance(company, dict):
                        continue
                    name = company.get("ai_name") or company.get("name") or company.get("ai")
                    print(" COMPANY", name, "keys", sorted(company.keys()),
                          "fleet", company.get("air_fleet"), "airports", company.get("airports"),
                          "engines", company.get("engine_mix"), "py", company.get("profit_year"),
                          "cv", company.get("company_value"))
