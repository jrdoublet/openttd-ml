"""Evidence audit for a frozen C66 V102 gain_short AIR-visible gate A40×3.

The economic gate is decided by the C66 harness, NOT this diagnostic. Use
annual snapshots only as active service stocks, never raw line construction.
Count only mutually-exclusive LOOP_OPS top-level posts, excluding nested C39
breakdowns and `sleep_left`. The categories include command/wait occupancy,
so they are NOT pure VM Squirrel instruction counts.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import mean

from analyse_p0_abandon_b20x10 import LINE, TOP


REF = "reference"
ON = "c121_air_visible_competition"
ARMS = ("OpexAI", "AAAHogEx")
MODES = ("air", "rail", "road")


def event_occupancy(path, years):
    posts = defaultdict(dict)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LINE.search(line)
        if match is None:
            continue
        year, post, count, ops, ticks = match.groups()
        year = int(year)
        if post in posts[year]:
            raise ValueError(f"duplicate LOOP_OPS {year=} {post=} {path=}")
        posts[year][post] = (int(ops), int(ticks))
    out = {}
    for year in years:
        if year not in posts or "_year" not in posts[year] or "sleep_left" not in posts[year]:
            raise ValueError(f"LOOP_OPS closure incomplete {path} {year}")
        out[year] = {
            "global_top_level_occupied": sum(posts[year][k][0] for k in TOP if k in posts[year]),
            "sleep_left": posts[year]["sleep_left"][0],
            "tick_budget": posts[year]["_year"][1] * 10_000,
            "orchestrator": posts[year].get("orchestrator", (0, 0))[0],
            "catalog_continuation": posts[year].get("catalog_continuation", (0, 0))[0],
        }
    return out


def summarize(report, json_path, *, year_start=1970, years=3, required_seeds=40):
    seeds = report["seeds"]
    if len(seeds) != required_seeds or len(set(seeds)) != len(seeds):
        raise ValueError("not all distinct preregistered seeds are present")
    if report["years"] != years or report["repeats"] != 1:
        raise ValueError("wrong time horizon or repetitions")
    if len(report["games"]) != 2 * required_seeds or report["failed_runs"]:
        raise ValueError("game failure or incomplete game records")
    if not all(g["game_ok"] and g["game_status"] == "complete" for g in report["games"]):
        raise ValueError("incomplete/failed run")
    pc = report["policy_comparison"]
    if pc["complete_pairs"] != required_seeds or not pc["metric_coverage_complete"]:
        raise ValueError("incomplete paired economic coverage")
    if pc.get("decision_rule", {}).get("rule") != "gain_short":
        raise ValueError("unexpected decision rule")
    trajectories = {p["seed"]: {r["year"]: r for r in p["annual_trajectory"]}
                    for p in pc["per_pair"]}
    if len(trajectories) != required_seeds:
        raise ValueError("duplicate/missing seeds in economic pairs")
    annual = {}
    for year in range(year_start, year_start + years):
        rows = [trajectories[s][year] for s in seeds]
        annual[str(year)] = {
            "mean_profit_year_opex_reference": round(mean(x["reference_opex"] for x in rows), 2),
            "mean_profit_year_opex_variant": round(mean(x["variant_opex"] for x in rows), 2),
            "mean_profit_year_variant_minus_ref": round(mean(x["policy_delta"] for x in rows), 2),
            "mean_opex_minus_aaa_reference": round(mean(x["reference_duel_gap"] for x in rows), 2),
            "mean_opex_minus_aaa_variant": round(mean(x["variant_duel_gap"] for x in rows), 2),
        }
    snapshots = report["line_telemetry"]["snapshots"]
    active = {}
    for row in snapshots:
        key = row["duel_policy_id"], row["arm"], row["seed"], row["year"]
        if key in active:
            raise ValueError(f"duplicate snapshot {key}")
        active[key] = row
    if len(active) != 4 * required_seeds * years:
        raise ValueError("missing annual line service snapshots")
    for year in range(year_start, year_start + years):
        for policy in (REF, ON):
            for arm in ARMS:
                grouped = [active[(policy, arm, seed, year)] for seed in seeds]
                qualified = [g for g in grouped if g["ok"] and not g["unresolved_vehicles"]]
                if not qualified:
                    raise ValueError("no qualified line telemetry")
                for mode in MODES:
                    prefix = f"{policy}_{arm}_{mode}"
                    annual[str(year)][f"active_services_{prefix}_mean"] = round(
                        mean(sum(line["mode"] == mode for line in g["lines"]) for g in qualified), 3)
                    annual[str(year)][f"active_services_{prefix}_n"] = len(qualified)
        # Matched stock comparison avoids biases when a few yearly telemetry
        # snapshots are individually unresolved even though game metrics pass.
        for arm in ARMS:
            same = [seed for seed in seeds
                    if all(active[(policy, arm, seed, year)]["ok"]
                           and not active[(policy, arm, seed, year)]["unresolved_vehicles"]
                           for policy in (REF, ON))]
            annual[str(year)][f"stock_qualified_cross_policy_{arm}_n"] = len(same)
            for mode in MODES:
                changes = [sum(line["mode"] == mode for line in active[(ON, arm, seed, year)]["lines"])
                           - sum(line["mode"] == mode for line in active[(REF, arm, seed, year)]["lines"])
                           for seed in same]
                annual[str(year)][f"active_services_delta_cross_policy_{arm}_{mode}_mean"] = (
                    round(mean(changes), 3) if changes else None)
    engine = json_path.with_name(json_path.stem + "_engine")
    close_years = tuple(range(year_start, year_start + years - 1))
    ops = {}
    for seed in seeds:
        a = event_occupancy(engine / f"{REF}_seed{seed}_r0.log", close_years)
        b = event_occupancy(engine / f"{ON}_seed{seed}_r0.log", close_years)
        ops[seed] = {year: b[year]["global_top_level_occupied"] - a[year]["global_top_level_occupied"]
                     for year in close_years}
    opcode = {str(year): {"n": len(seeds),
                          "mean_delta_top_level": round(mean(ops[s][year] for s in seeds), 2),
                          "variant_lower": sum(ops[s][year] < 0 for s in seeds),
                          "variant_higher": sum(ops[s][year] > 0 for s in seeds)}
              for year in close_years}
    return {"campaign": report["campaign_id"], "bundle": report["source_bundle_sha256"],
            "harness_gate_verdict": pc["verdict"], "paired_seeds": required_seeds,
            "healthy_games": len(report["games"]), "snapshot_count": len(snapshots),
            "economic_metric": "profit_year", "primary": pc["aggregates"]["profit_year"],
            "company_value": pc["aggregates"]["company_value"],
            "annual": annual, "loop_ops_top_level": opcode,
            "limitations": [
                "The V102 harness decides the full gate using Wilcoxon exact, mean useful gain and value guard.",
                "A40×3 ends in 1972 and CANNOT establish changed profits or construction in 1973.",
                "Annual service snapshots count currently active grouped services, NOT raw new line builds.",
                "LOOP_OPS top-level is occupancy and may include command/wait, not precise useful Squirrel VM instructions.",
                "The existing C121 visible-competition toggle alters demand estimates for both new AIR projects and existing fleet; attribution to one alone unproven.",
                "The old c121_visible_flux flag (previously rejected) is independent and not under test here.",
                "Diagnostic probes/script-debug are identical across arms but can alter trajectories relative to probe-free games.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("refusing to overwrite existing analysis")
    report = summarize(json.loads(args.c66.read_text(encoding="utf-8")), args.c66)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gate": report["harness_gate_verdict"], "primary": report["primary"],
                      "company_value": report["company_value"], "annual": report["annual"],
                      "loop_ops_top_level": report["loop_ops_top_level"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
