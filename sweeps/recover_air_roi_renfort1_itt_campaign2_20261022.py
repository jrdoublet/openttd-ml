"""Recover the C66.4 summary after postprocessing OOM, without replaying games.

Reads the immutable checkpoint JSONL once. The original 40 simulation logs,
monthly checkpoints, and source manifest remain unchanged. Only fields used
by benchmark health validation and policy comparison are retained in RAM.

Offline postprocessing only: ``--write`` creates a recovered campaign JSON.
Use ``--results-dir`` pointing to controlled copies of historical inputs;
the command refuses to overwrite an existing summary.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

import bench_1v1_5y_20seeds as bench
from bench_v2 import SUCCESS_METRICS
from game_health import (assess_game, annotate_summary, reconcile_assessment,
                         expected_last_year, expected_last_checkpoint)


CHECKPOINT_FIELDS = {
    "run", "date", "company_value", "performance_history", "income_last_year",
    "expenses_last_year", "delivered_cargo_last_quarter", "profit", "profit_year",
    "profit_year_quarters_available", "profit_year_quarters_valid",
    "profit_year_coverage", "median_station_rating", "n_station_ratings", "money",
    "current_loan", "months_of_bankruptcy", "physical_counters_version",
    "qualified_modes", "vehs_chunk_valid", "vehs_chunk_error", "stnn_chunk_valid",
    "stnn_chunk_error", "n_vehicles", "vehicle_pool_entries",
    "total_vehicle_pool_entries", "primary_vehicles", "primary_vehicles_by_mode",
    "capacities_by_cargo", "fleet_status", "unclassified_vehicles", "n_stations",
    "n_multimodal_stations", "stations_by_facility", "unresolved_stations",
    "company_present", "engine_failure", "campaign_id", "game_id",
    "source_bundle_sha256", "duel_policy_id", "policy_id", "company_slot",
    "selection_kopcodes_samples", "selection_kopcodes_total",
    "selection_kopcodes_mean", "selection_kopcodes_max",
    "observed_opcode_schema", "observed_opcodes_total", "observed_opcode_samples",
    "observed_opcode_components", "observed_opcode_complete_cpu",
    "rail_budget_sign_schema", "rail_budget_sign_coverage",
    "rail_budget_sign_by_year", "rail_budget_sign_invalid",
    "rail_budget_sign_conflicts", "qualified_primary_vehicles",
    "unqualified_primary_vehicles",
} | set(bench.AIR_STRUCTURAL_METRICS) | set(bench.TOWN_GROWTH_SUMMARY_METRICS) | set(bench.C75_BYPASS_SUMMARY_METRICS)


def recover(campaign: str, directory: Path, *, write: bool = False):
    manifest_path = directory / (campaign + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    options = manifest["execution"]["options"]
    bundle_hash = manifest["source_bundle"]["sha256"]
    checkpoint = directory / (campaign + ".jsonl")
    if options["campaign"] != campaign or manifest["campaign_id"] != campaign:
        raise ValueError("Campaign identity mismatch")
    if options["years"] != 10 or options["repeats"] != 1 or len(options["seeds"]) != 20:
        raise ValueError("Not the registered 20x10 design")

    grouped = defaultdict(list)
    rows_by_year = {}
    count = 0
    by_policy = defaultdict(int)
    with checkpoint.open("r", encoding="utf-8") as stream:
        for lineno, raw in enumerate(stream, start=1):
            if not raw.endswith("\n"):
                raise ValueError(f"Unterminated checkpoint at line {lineno}")
            full = json.loads(raw)
            rec = {k: full[k] for k in CHECKPOINT_FIELDS if k in full}
            rec["openttd_output"] = ""
            name = rec.get("game_id")
            if rec.get("campaign_id") != campaign or rec.get("source_bundle_sha256") != bundle_hash:
                raise ValueError(f"Checkpoint source mismatch at line {lineno}")
            if rec.get("duel_policy_id") not in (options["policy_id"], options["variant_policy_id"]):
                raise ValueError(f"Unknown policy at line {lineno}")
            if not name or not isinstance(rec.get("run"), list) or len(rec["run"]) != 3:
                raise ValueError(f"Missing identity at line {lineno}")
            if rec["run"][1] not in options["seeds"] or rec["run"][2] != 0:
                raise ValueError(f"Unknown seed / repeat at line {lineno}")
            grouped[name].append(rec)
            by_policy[rec["duel_policy_id"]] += 1
            year = int(rec["date"][:4])
            if 1970 <= year < 1980:
                year_key = (rec["duel_policy_id"], *rec["run"], year)
                previous = rows_by_year.get(year_key)
                if previous is None or previous["date"] < rec["date"]:
                    rows_by_year[year_key] = {
                        k: rec.get(k) for k in
                        ("run", "date", "duel_policy_id", options["primary_metric"],
                         *bench.AIR_STRUCTURAL_METRICS)
                    }
            count += 1

    summary, games = [], []
    for game_id, recs in sorted(grouped.items()):
        first = recs[0]
        seed = first["run"][1]
        policy = first["duel_policy_id"]
        if len({(r["duel_policy_id"], r["run"][1], r["run"][2]) for r in recs}) != 1:
            raise ValueError(f"Mixed identity in {game_id}")
        expected_game = f"{campaign}:policy={policy}:s{seed}:r0"
        if game_id != expected_game:
            raise ValueError(f"Wrong game ID: {game_id}, expected {expected_game}")
        log = directory / (campaign + "_engine") / f"{policy}_seed{seed}_r0.log"
        if not log.is_file():
            raise ValueError(f"Missing script log: {log}")
        assessment = assess_game(recs, starting_year=1970, years=10,
                                 engine_log_path=str(log))
        part = bench.summarise(recs, expected_last_year=expected_last_year(1970, 10),
                               expected_savegames=120)
        part = bench._stamp_structural_metrics(part, recs)
        annotated = annotate_summary(part, recs, assessment)
        for row in annotated:
            if row["status"] == "bankrupt":
                for metric in SUCCESS_METRICS:
                    if row.get(metric) is None:
                        row[metric] = 0
            row.update({"campaign_id": campaign, "policy_id": policy if row["arm"] == "OpexAI" else "AAAHogEx",
                        "duel_policy_id": policy, "game_id": game_id,
                        "company_slot": 0 if row["arm"] == "OpexAI" else 1,
                        "source_bundle_sha256": bundle_hash})
        assessment = reconcile_assessment(assessment, annotated)
        summary.extend(annotated)
        games.append({
            "campaign_id": campaign, "policy_id": policy, "game_id": game_id,
            "source_bundle_sha256": bundle_hash, "seed": seed, "repeat": 0,
            "game_ok": assessment["game_ok"], "game_status": assessment["game_status"],
            "engine_log_path": str(log),
            "expected_last_checkpoint": assessment["expected_last_checkpoint"],
            "unattributed_errors": assessment["unattributed_errors"],
            "companies": {arm: {"status": data["status"], "run_ok": data["run_ok"],
                                 "failure_reason": data["failure_reason"],
                                 "horizon_complete": data["horizon_complete"],
                                 "activity": data["activity"]["signal"]}
                          for arm, data in assessment["companies"].items()},
        })

    expected = {(policy, seed) for seed in options["seeds"] for policy in
                (options["policy_id"], options["variant_policy_id"])}
    observed = {(g["policy_id"], g["seed"]) for g in games}
    if observed != expected or len(games) != 40 or len(summary) != 80:
        raise ValueError(f"Incomplete or duplicated games: missing={expected-observed}, extra={observed-expected}")

    comparison = bench.build_policy_comparison(
        summary, list(rows_by_year.values()),
        seeds=options["seeds"], repeats=1,
        reference_policy_id=options["policy_id"],
        variant_policy_id=options["variant_policy_id"],
        primary_metric=options["primary_metric"],
        min_useful_primary_delta=options["min_useful_primary_delta"],
        min_useful_primary_delta_pct=options["min_useful_primary_delta_pct"],
        required_seeds=options["required_seeds"], required_years=options["required_years"],
        value_guard_max_loss_pct=options["value_guard_max_loss_pct"],
        starting_year=1970, years=10, decision_rule=options["decision_rule"],
    )
    report = {
        "campaign_id": campaign, "policy_id": options["policy_id"],
        "source_bundle_sha256": bundle_hash,
        "manifest_path": str(manifest_path), "manifest_sha256": None,
        "years": 10, "seeds": options["seeds"], "repeats": 1, "start_year": 1970,
        "map_size": options["map_size"], "games": games, "summary": summary,
        "policy_comparison": comparison,
        "failed_runs": [
            {"game_id": s["game_id"], "arm": s["arm"], "seed": s["seed"],
             "status": s.get("status"), "failure_reason": s.get("failure_reason")}
            for s in summary if not s["run_ok"]],
        "recovery_provenance": {
            "reason": "docker_oom_after_40_checkpoints",
            "method": "streaming original JSONL and 40 original engine logs; benchmark health and comparison functions",
            "checkpoint_file": str(checkpoint), "checkpoint_rows": count,
            "policy_checkpoint_rows": dict(by_policy),
            "recovered_without_simulation": True,
            "full_line_telemetry_omitted_from_recovery_summary": True,
        },
    }
    if write:
        import hashlib
        report["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        out = directory / (campaign + ".json")
        if out.exists():
            raise FileExistsError(f"Will not overwrite existing campaign summary: {out}")
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", default="airr1_itt_month_20x10_20261022_b")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = recover(args.campaign, args.results_dir, write=args.write)
    from collections import Counter
    statuses = Counter((g["game_status"], bool(g["game_ok"])) for g in result["games"])
    compare = result["policy_comparison"]
    print("Games:", statuses)
    print("Pairs:", compare["complete_pairs"], "/", compare["planned_pairs"],
          "complete:", compare["comparison_complete"])
    print("Company annual profit:", compare["aggregates"]["profit_year"]["policy_delta"])
    print("Company value ratio:", compare["aggregates"]["company_value"]["policy_ratio"])


if __name__ == "__main__":
    main()
