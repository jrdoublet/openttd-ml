#!/usr/bin/env python3
import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "results" / "c121_projectreal_adaptive_pressure_5x6_20260929_analysis.json"
d = json.loads(p.read_text())
for row in d["policy_comparison"]["per_pair"]:
    m = row["metrics"]
    a = row["air_structural_metrics"]
    print(
        row["seed"],
        "profit", m["profit_year"]["policy_delta"],
        "gap", m["profit_year"]["duel_gap_evolution"],
        "value", m["company_value"]["policy_delta"],
        "value_gap", m["company_value"]["duel_gap_evolution"],
        "opex_slots", a["airport_slots_opex"]["policy_delta"],
        "aaa_slots", a["airport_slots_aaahogex"]["policy_delta"],
        "aaa_2_0", a["airport_towns_aaahogex_2_opex_0"]["policy_delta"],
        "opex_towns", a["airport_towns_opex_present"]["policy_delta"],
    )
