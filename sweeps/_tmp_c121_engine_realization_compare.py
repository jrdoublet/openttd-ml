#!/usr/bin/env python3
import json

d = json.load(open("results/c121_engine_realization_seed42_6y_20260929.json", encoding="utf-8"))
for row in d.get("summary", []):
    if row.get("arm") != "OpexAI" or row.get("seed") != 42:
        continue
    print(row.get("policy_id"),
          "profit_year", row.get("profit_year"),
          "value", row.get("company_value"),
          "money", row.get("money"),
          "vehicles_by_mode", row.get("primary_vehicles_by_mode"),
          "stations", row.get("stations_by_facility"),
          "capacities", row.get("capacities_by_cargo"))
