#!/usr/bin/env python3
import json
import statistics as stats

PATH = "results/c121_first_live_growth_5x6_20261001_r2.json"
REF = "c121_base_live_shadow"
VAR = "c121_first_live_growth_bal90_fallback"

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
    print(year, "py_mean", round(stats.mean(py), 1), "gap_mean", round(stats.mean(gap), 1))

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
for seed in d["seeds"]:
    ref = finals.get((REF, seed), {})
    var = finals.get((VAR, seed), {})
    print(seed, "ref", ref, "var", var)
for field in ("lines", "vehicles", "one_plane", "two_plus"):
    vals = [finals[(VAR, seed)][field] - finals[(REF, seed)][field] for seed in d["seeds"]]
    print("delta_" + field, round(stats.mean(vals), 2), vals)

# Conservative annual-snapshot 1->2 crossings on stable Opex local line keys.
for label in ("crossings", "ever_two"):
    vals = []
    for seed in d["seeds"]:
        counts = {}
        for policy in (REF, VAR):
            snaps = sorted((s for s in lt.get("snapshots") or []
                            if s.get("arm") == "OpexAI" and s.get("duel_policy_id") == policy
                            and s.get("seed") == seed), key=lambda s: s.get("year", -1))
            prior = {}
            seen_cross = set()
            seen_two = set()
            for snap in snaps:
                current = {line.get("line_key_local"): int(line.get("vehicles") or 0)
                           for line in snap.get("lines") or [] if line.get("mode") == "air"}
                for key, n in current.items():
                    if n >= 2:
                        seen_two.add(key)
                    if key in prior and prior[key] == 1 and n >= 2:
                        seen_cross.add(key)
                prior = current
            counts[policy] = len(seen_cross if label == "crossings" else seen_two)
        vals.append(counts[VAR] - counts[REF])
        print(label, seed, "ref", counts[REF], "var", counts[VAR], "delta", counts[VAR] - counts[REF])
    print(label + "_delta_mean", round(stats.mean(vals), 2), vals)
