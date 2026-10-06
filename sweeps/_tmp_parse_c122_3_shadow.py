#!/usr/bin/env python3
from pathlib import Path
import json
import re


BASE = Path("results/c122_3_shadow_control_smoke_seed42_1x3_20260929_r3")
DATA = json.loads(BASE.with_suffix(".json").read_text(encoding="utf-8"))
LOGDIR = Path(str(BASE) + "_engine")


def summary(policy, arm):
    for row in DATA["summary"]:
        if row.get("duel_policy_id") == policy and row.get("arm") == arm:
            return row
    raise KeyError((policy, arm))


ref_o = summary("c121_shadow_classifier_control", "OpexAI")
ref_a = summary("c121_shadow_classifier_control", "AAAHogEx")
var_o = summary("c122_3_regime_priority", "OpexAI")
var_a = summary("c122_3_regime_priority", "AAAHogEx")

ref_gap = ref_o["profit_year"] - ref_a["profit_year"]
var_gap = var_o["profit_year"] - var_a["profit_year"]

print("opex_profit_delta", var_o["profit_year"] - ref_o["profit_year"])
print("opex_value_delta", var_o["company_value"] - ref_o["company_value"])
print("opex_value_pct", 100.0 * (var_o["company_value"] / ref_o["company_value"] - 1.0))
print("ref_gap", ref_gap)
print("var_gap", var_gap)
print("gap_delta", var_gap - ref_gap)
for key in (
    "airport_slots_opex",
    "airport_towns_opex_present",
    "airport_towns_aaahogex_2_opex_0",
    "airport_towns_opex_2_aaahogex_0",
    "airport_towns_shared_1_1",
    "primary_vehicles",
):
    print(key, ref_o[key], "->", var_o[key], "delta", var_o[key] - ref_o[key])

for policy in ("c121_shadow_classifier_control", "c122_3_regime_priority"):
    path = LOGDIR / f"{policy}_seed42_r0.log"
    text = path.read_text(encoding="utf-8", errors="replace")
    promotions = text.count("C122_PROMOTE")
    exposures = text.count("C122_EXPOSURE")
    locks = re.findall(r"C121_STRATEGY_LOCK[^\r\n]*", text)
    exposure_rows = re.findall(
        r"C122_EXPOSURE date=(\d+) air=(\d+) new=(\d+) potential_inversions=(\d+) "
        r"top_air_global_rank=(-?\d+) top_air_score=([^ ]+) best_new_global_rank=(-?\d+) "
        r"best_new_air_rank=(-?\d+) best_new_claims=(\d+) best_new_score=([^ ]+) "
        r"best_new_tier=(-?\d+) same_tier_blockers=(\d+) promotions=(\d+)",
        text,
    )
    print("policy", policy, "promotions", promotions, "exposures", exposures)
    print("locks", locks)
    if exposure_rows:
        print("exposure_with_new", sum(int(row[2]) > 0 for row in exposure_rows))
        print("exposure_with_potential", sum(int(row[3]) > 0 for row in exposure_rows))
        print("exposure_new_sum", sum(int(row[2]) for row in exposure_rows))
        print("exposure_potential_sum", sum(int(row[3]) for row in exposure_rows))
        print("promotion_count_final", max(int(row[12]) for row in exposure_rows))
