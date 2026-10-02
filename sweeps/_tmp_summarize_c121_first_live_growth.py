#!/usr/bin/env python3
import json
import statistics as stats
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "results/c121_first_live_growth_5x6_20261001_r1.json"
d = json.load(open(path, encoding="utf-8"))
pairs = d["policy_comparison"]["per_pair"]
reference_policy = d["policy_comparison"]["reference_policy_id"]
variant_policy = d["policy_comparison"]["variant_policy_id"]

for metric in ("profit_year", "company_value", "primary_vehicles"):
    deltas = [p["metrics"][metric]["policy_delta"] for p in pairs]
    gaps = [p["metrics"][metric]["duel_gap_evolution"] for p in pairs]
    print(metric, "deltas", deltas, "mean", round(stats.mean(deltas), 1),
          "median", stats.median(deltas), "gap_mean", round(stats.mean(gaps), 1), "gaps", gaps)

for key in ("airport_slots_opex", "airport_towns_opex_present",
            "airport_towns_aaahogex_2_opex_0", "airport_towns_shared_1_1"):
    vals = [p["air_structural_metrics"][key]["policy_delta"] for p in pairs]
    print(key, vals, "mean", round(stats.mean(vals), 2))

print("annual")
for idx, year in enumerate(range(1970, 1976)):
    py = [p["annual_trajectory"][idx]["policy_delta"] for p in pairs]
    gap = [p["annual_trajectory"][idx]["variant_duel_gap"] - p["annual_trajectory"][idx]["reference_duel_gap"] for p in pairs]
    print(year, "py_mean", round(stats.mean(py), 1), "gap_mean", round(stats.mean(gap), 1))

lt = d.get("line_telemetry")
if isinstance(lt, dict):
    print("line_telemetry_keys", sorted(lt.keys()))
    print("line_telemetry_snapshots", len(lt.get("snapshots") or []))
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
    print("final_air_by_pair")
    for seed in d["seeds"]:
        ref = finals.get((reference_policy, seed), {})
        var = finals.get((variant_policy, seed), {})
        print(seed, "ref", ref, "var", var,
              "delta_lines", var.get("lines", 0) - ref.get("lines", 0),
              "delta_air_vehicles", var.get("vehicles", 0) - ref.get("vehicles", 0))
    for field in ("lines", "vehicles", "one_plane", "two_plus"):
        vals = [
            finals[(variant_policy, seed)][field]
            - finals[(reference_policy, seed)][field]
            for seed in d["seeds"]
        ]
        print("final_air_delta_" + field, vals, "mean", round(stats.mean(vals), 2))

    # Annual line telemetry cannot see a 1->2->... transition entirely between two
    # snapshots, but it can count conservative observed crossings on stable line keys.
    crossings = {}
    ever_two = {}
    for policy in (reference_policy, variant_policy):
        for seed in d["seeds"]:
            snaps = sorted(
                (s for s in lt.get("snapshots") or []
                 if s.get("arm") == "OpexAI" and s.get("duel_policy_id") == policy
                 and s.get("seed") == seed),
                key=lambda s: s.get("year", -1),
            )
            prior = {}
            seen_cross = set()
            seen_two = set()
            for snap in snaps:
                current = {
                    line.get("line_key_local"): int(line.get("vehicles") or 0)
                    for line in snap.get("lines") or [] if line.get("mode") == "air"
                }
                for key, n in current.items():
                    if n >= 2:
                        seen_two.add(key)
                    if key in prior and prior[key] == 1 and n >= 2:
                        seen_cross.add(key)
                prior = current
            crossings[(policy, seed)] = len(seen_cross)
            ever_two[(policy, seed)] = len(seen_two)
    for label, values in (("observed_annual_1to2_crossings", crossings), ("ever_seen_two_plus", ever_two)):
        ds = []
        for seed in d["seeds"]:
            ref = values[(reference_policy, seed)]
            var = values[(variant_policy, seed)]
            ds.append(var - ref)
            print(label, seed, "ref", ref, "var", var, "delta", var - ref)
        print(label + "_delta_mean", round(stats.mean(ds), 2), ds)
