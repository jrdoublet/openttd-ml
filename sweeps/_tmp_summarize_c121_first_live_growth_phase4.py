#!/usr/bin/env python3
import json
import statistics as stats

PATH = "results/c121_first_live_growth_phase4_5x6_20261001_r1.json"
REF = "c121_base_live_shadow"
VAR = "c121_first_live_growth_bal90_phase4"

d = json.load(open(PATH, encoding="utf-8"))
pairs = d["policy_comparison"]["per_pair"]
print("pairs", d["policy_comparison"]["complete_pairs"], "/", d["policy_comparison"]["planned_pairs"])
for metric in ("profit_year", "company_value", "primary_vehicles"):
    deltas = [p["metrics"][metric]["policy_delta"] for p in pairs]
    gaps = [p["metrics"][metric]["duel_gap_evolution"] for p in pairs]
    print(metric, "delta_mean", round(stats.mean(deltas), 1), "median", stats.median(deltas),
          "wins", sum(x > 0 for x in deltas), "losses", sum(x < 0 for x in deltas),
          "gap_mean", round(stats.mean(gaps), 1), "deltas", deltas, "gaps", gaps)
for key in ("airport_slots_opex", "airport_towns_opex_present",
            "airport_towns_aaahogex_2_opex_0", "airport_towns_shared_1_1"):
    vals = [p["air_structural_metrics"][key]["policy_delta"] for p in pairs]
    print(key, "mean", round(stats.mean(vals), 2), "deltas", vals)
print("annual")
for idx, year in enumerate(range(1970, 1976)):
    py = [p["annual_trajectory"][idx]["policy_delta"] for p in pairs]
    gap = [p["annual_trajectory"][idx]["variant_duel_gap"] - p["annual_trajectory"][idx]["reference_duel_gap"] for p in pairs]
    slots = [p["annual_trajectory"][idx]["air_structural_metrics"]["airport_slots_opex"]["policy_delta"] for p in pairs]
    print(year, "py_mean", round(stats.mean(py), 1), "gap_mean", round(stats.mean(gap), 1),
          "slots_mean", round(stats.mean(slots), 2))

lt = d.get("line_telemetry") or {}
finals = {}
for snap in lt.get("snapshots") or []:
    if snap.get("arm") != "OpexAI" or snap.get("year") != 1975:
        continue
    key = (snap.get("duel_policy_id"), snap.get("seed"))
    air = [line for line in snap.get("lines") or [] if line.get("mode") == "air"]
    finals[key] = {
        "lines": len(air),
        "vehicles": sum(int(line.get("vehicles") or 0) for line in air),
        "one_plane": sum(int(line.get("vehicles") or 0) == 1 for line in air),
        "two_plus": sum(int(line.get("vehicles") or 0) >= 2 for line in air),
    }
print("final_air")
for field in ("lines", "vehicles", "one_plane", "two_plus"):
    vals = [finals[(VAR, seed)][field] - finals[(REF, seed)][field] for seed in d["seeds"]]
    print("delta_" + field, round(stats.mean(vals), 2), vals)
