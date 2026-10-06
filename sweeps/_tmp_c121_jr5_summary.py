#!/usr/bin/env python3
import json

d = json.load(open("results/c121_current_5x6_jr5_20260929.json", encoding="utf-8"))
pc = d["policy_comparison"]
for metric in ("profit_year", "company_value"):
    a = pc["aggregates"][metric]
    print(metric)
    print("delta", a["policy_delta"])
    print("ratio", a["policy_ratio"])
print("adoption_sample_complete", pc.get("adoption_sample_complete"))
print("paired_count", len(pc.get("paired", [])))
print("pc_keys", sorted(pc.keys()))
print("top_keys", sorted(d.keys()))
for k, v in d.items():
    if isinstance(v, list) and v and isinstance(v[0], dict):
        print("top_list", k, "len", len(v), "first_keys", sorted(v[0].keys()))
for k, v in pc.items():
    if isinstance(v, list):
        print("list", k, "len", len(v))
        if v and isinstance(v[0], dict):
            print("first_keys", sorted(v[0].keys()))
for p in pc.get("per_pair", []):
    m = p.get("metrics", {})
    print("seed", p.get("seed"),
          "profit", m.get("profit_year", {}).get("policy_delta"),
          "value", m.get("company_value", {}).get("policy_delta"),
          "air", p.get("air_structural_metrics"))

for row in d.get("summary", []):
    if row.get("seed") not in (42, 1234) or row.get("arm") != "OpexAI":
        continue
    print("SUMMARY", row.get("seed"), row.get("policy_id"),
          "profit_year", row.get("profit_year"),
          "value", row.get("company_value"),
          "money", row.get("money"),
          "vehicles_by_mode", row.get("primary_vehicles_by_mode"),
          "stations", row.get("stations_by_facility"),
          "capacities", row.get("capacities_by_cargo"))

lt = d.get("line_telemetry", {})
print("line_telemetry_keys", sorted(lt.keys()) if isinstance(lt, dict) else type(lt).__name__)
if isinstance(lt, dict):
    for k, v in lt.items():
        if isinstance(v, list):
            print("lt_list", k, len(v), sorted(v[0].keys()) if v and isinstance(v[0], dict) else None)
