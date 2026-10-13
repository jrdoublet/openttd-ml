"""Audit an already completed P0 second-abandon-check C66 paired campaign.

Only mutually exclusive LOOP_OPS top-level posts are added.  They measure
tick-window occupancy (including commands/waits), NOT pure Squirrel VM opcodes.
Service counts are annual active services, NOT new line construction events.
This program never runs Docker and never modifies its input artifacts.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re
from statistics import mean, median


TOP = {"events", "save_projection", "station_flux", "c117_sample", "c117_skip",
       "orchestrator", "catalog_continuation", "catalog_continuation_check",
       "rail_throughput", "c67_hook"}
LINE = re.compile(r"\[script:\d+\] \[0\] \[I\] LOOP_OPS y=(\d+) post=([^ ]+) n=(\d+) ops=(\d+) tk=(\d+)")
REF, VAR = "reference", "p0_abandon_second_check_skip"
YEARS = range(1970, 1979)


def percentile(xs, fraction):
    xs = sorted(xs)
    i = fraction * (len(xs) - 1)
    lo = int(i)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (i - lo)


def stats(xs):
    assert xs
    rng = random.Random(0)
    draws = [mean(rng.choices(xs, k=len(xs))) for _ in range(20_000)]
    return {"n": len(xs), "mean": round(mean(xs), 3), "median": round(median(xs), 3),
            "wins_variant_lower": sum(x < 0 for x in xs),
            "losses_variant_higher": sum(x > 0 for x in xs),
            "ties": sum(x == 0 for x in xs),
            "bootstrap95_mean": [round(percentile(draws, q), 3) for q in (.025, .975)]}


def loops(path):
    posts = defaultdict(dict)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LINE.search(line)
        if match is None:
            continue
        year, post, _n, ops, ticks = match.groups()
        year = int(year)
        if post in posts[year]:
            raise ValueError(f"duplicate LOOP_OPS {path} {year} {post}")
        posts[year][post] = (int(ops), int(ticks))
    if not set(YEARS).issubset(posts):
        raise ValueError(f"incomplete LOOP_OPS years {path}: {sorted(posts)}")
    years = {}
    for year in YEARS:
        p = posts[year]
        if "_year" not in p or "sleep_left" not in p:
            raise ValueError(f"LOOP_OPS year closure missing {path} {year}")
        years[year] = {
            "occupied_top": sum(p[k][0] for k in TOP if k in p),
            "sleep_left": p["sleep_left"][0],
            "tick_budget": p["_year"][1] * 10_000,
            "orchestrator": p.get("orchestrator", (0, 0))[0],
            "catalog_continuation": p.get("catalog_continuation", (0, 0))[0],
        }
    return years


def audit(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    assert len(d["seeds"]) == 20 and len(set(d["seeds"])) == 20
    assert d["years"] == 10 and d["repeats"] == 1
    assert len(d["games"]) == 40 and len(d["summary"]) == 80
    assert d["failed_runs"] == []
    assert d["source_bundle_sha256"] == "6f4657e035f799123fc1a1df4decda57ccf2ea41fda3404b528679f37bdc5f05"
    assert d["policy_comparison"]["complete_pairs"] == 20
    assert d["policy_comparison"]["metric_coverage_complete"]
    assert all(g["game_ok"] is True and g["game_status"] == "complete" for g in d["games"])
    assert all(r["game_ok"] and r["run_ok"] and r["physical_ok"] and
               r["horizon_complete"] and r["profit_year_quarters_valid"] == 4
               and r["vehs_chunk_valid"] and r["stnn_chunk_valid"] and
               r["script_errors"] == [] for r in d["summary"])

    by_policy = {(p["seed"], p["repeat"]): p for p in d["policy_comparison"]["per_pair"]}
    assert len(by_policy) == 20 and all(p["complete"] for p in by_policy.values())
    telem = d["line_telemetry"]["snapshots"]
    snap = {(t["duel_policy_id"], t["arm"], t["seed"], t["year"]): t for t in telem}
    assert len(telem) == len(snap) == 800
    assert all(t["ok"] is True for t in telem)
    unresolved = [{"policy": t["duel_policy_id"], "arm": t["arm"],
                   "seed": t["seed"], "year": t["year"],
                   "vehicle_count": len(t["unresolved_vehicles"])}
                  for t in telem if t["unresolved_vehicles"]]
    policies = (REF, VAR)
    annual = {}
    for year in range(1970, 1980):
        a = [next(x for x in p["annual_trajectory"] if x["year"] == year)
             for p in by_policy.values()]
        annual[str(year)] = {
            "opex_profit_ref_mean": round(mean(x["reference_opex"] for x in a), 2),
            "opex_profit_variant_mean": round(mean(x["variant_opex"] for x in a), 2),
            "opex_profit_variant_minus_ref_mean": round(mean(x["policy_delta"] for x in a), 2),
            "opex_vs_aaa_ref_gap_mean": round(mean(x["reference_duel_gap"] for x in a), 2),
            "opex_vs_aaa_variant_gap_mean": round(mean(x["variant_duel_gap"] for x in a), 2),
        }
        for policy in policies:
            for arm in ("OpexAI", "AAAHogEx"):
                for mode in ("air", "rail", "road"):
                    counts = [sum(line["mode"] == mode
                                  for line in snap[(policy, arm, seed, year)]["lines"])
                              for seed in d["seeds"]
                              if not snap[(policy, arm, seed, year)]["unresolved_vehicles"]]
                    annual[str(year)][f"active_{policy}_{arm}_{mode}_mean"] = round(mean(counts), 3)
                    annual[str(year)][f"active_{policy}_{arm}_{mode}_qualified_n"] = len(counts)

    logs = path.with_name(path.stem + "_engine")
    per_seed = {}
    for seed in d["seeds"]:
        left = loops(logs / f"{REF}_seed{seed}_r0.log")
        right = loops(logs / f"{VAR}_seed{seed}_r0.log")
        per_seed[str(seed)] = {str(year): {
            "reference": left[year], "variant": right[year],
            "delta_occupied": right[year]["occupied_top"] - left[year]["occupied_top"],
        } for year in YEARS}

    total = [sum(per_seed[str(seed)][str(y)]["delta_occupied"] for y in YEARS)
             for seed in d["seeds"]]
    global_ops = {
        "all_years_1970_1978_delta": stats(total),
        "by_year": {str(y): stats([per_seed[str(s)][str(y)]["delta_occupied"]
                                  for s in d["seeds"]]) for y in YEARS},
        "ref_mean_occupied_1970_1978": round(mean(sum(per_seed[str(s)][str(y)]["reference"]["occupied_top"]
                                                     for y in YEARS) for s in d["seeds"]), 2),
        "variant_mean_occupied_1970_1978": round(mean(sum(per_seed[str(s)][str(y)]["variant"]["occupied_top"]
                                                         for y in YEARS) for s in d["seeds"]), 2),
    }
    primary = d["policy_comparison"]
    return {"campaign": d["campaign_id"], "bundle": d["source_bundle_sha256"],
            "health": {"games": 40, "paired_seeds": 20, "summary_company_rows": 80,
                       "annual_active_service_snapshots": 800,
                       "unresolved_vehicle_snapshots": len(unresolved),
                       "unresolved_vehicle_details": unresolved,
                       "script_errors": 0, "failed_runs": 0},
            "terminal": {
                "profit_delta": primary["aggregates"]["profit_year"]["policy_delta"],
                "profit_ratio": primary["aggregates"]["profit_year"]["policy_ratio"],
                "company_value_delta": primary["aggregates"]["company_value"]["policy_delta"],
                "company_value_ratio": primary["aggregates"]["company_value"]["policy_ratio"],
                "harness_non_erosion_verdict": primary["verdict"],
                "not_an_adoption_verdict": True,
            }, "annual_trajectory": annual, "top_level_loop_ops": global_ops,
            "per_seed_42_100_999": {
                str(s): {"profit_by_year": {str(y): next(x for x in by_policy[(s, 0)]["annual_trajectory"]
                                                        if x["year"] == y)["policy_delta"]
                                          for y in range(1970, 1974)},
                         "occupied_by_year": {str(y): per_seed[str(s)][str(y)]["delta_occupied"]
                                              for y in range(1970, 1974)}} for s in (42, 100, 999)},
            "limitations": [
                "LOOP_OPS top-level is non-overlapping and approximates tick-window occupation; not pure VM instructions.",
                "1979 terminal profit requires a 1979 simulation; LOOP_OPS closures cover 1970-1978.",
                "Yearly active services are not construction counts or unique new project attempts.",
                "No strict economic conversion causality follows from a narrow duplicate-check change.",
                "Separate policy maps may diverge, including AAAHogEx trajectories; pair the two Opex arms by seed only.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("json", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    result = audit(a.json)
    if a.out:
        if a.out.exists():
            p.error(f"refusing to overwrite {a.out}")
        a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"health": result["health"], "terminal": result["terminal"],
                      "top_level_loop_ops": result["top_level_loop_ops"],
                      "first_four_years": {str(y): result["annual_trajectory"][str(y)]
                                           for y in range(1970, 1974)},
                      "per_seed_42_100_999": result["per_seed_42_100_999"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
