"""Audit paired C66 20x10 health and physical *stocks*, not build causality.

Read a completed C66 JSON (summary + games).  VEHS/STNN provide final stocks;
``activity`` counts changes between checkpoints, not actual build events.
Without separately qualified, timestamped construction telemetry, counts of
AIR/RAIL lines built and their chronology are UNKNOWN, never zero.  In
particular, airports are not AIR lines and rail stations are not RAIL lines.

Run without creating files:
  python -B sweeps/analyse_p0_topk_construction.py results/C66.json --summary-only
Optional --out stores the full analysis (never the input or existing reports).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


METRICS = ("company_value", "profit_year", "primary_vehicles", "n_vehicles",
           "n_stations", "months_of_bankruptcy")
MODES = ("air", "rail")
FACILITIES = {"air": "airport", "rail": "rail"}
ACTIVITY = ("fleet_changes", "network_changes",
            "months_since_fleet_or_network_change", "value_increases")
CHECKPOINT_FIELDS = {
    "air_vehicles": ("primary_vehicles_by_mode", "air", "vehs_chunk_valid"),
    "rail_vehicles": ("primary_vehicles_by_mode", "rail", "vehs_chunk_valid"),
    "airports": ("stations_by_facility", "airport", "stnn_chunk_valid"),
    "rail_stations": ("stations_by_facility", "rail", "stnn_chunk_valid"),
}


def nonnegative(value):
    """Treat missing, bool, malformed and negative as unavailable, not zero."""
    return value if type(value) is int and value >= 0 else None


def finite_number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def pair_delta(reference, variant):
    return variant - reference if reference is not None and variant is not None else None


def seed_repeat(record):
    if not isinstance(record, dict):
        return None
    seed, repeat = nonnegative(record.get("seed")), nonnegative(record.get("repeat"))
    return (seed, repeat) if seed is not None and repeat is not None else None


def load_checkpoints(path):
    """Index original C66 JSONL Opex rows only; never infer lines from stock.

    Rows have a `run` triple and `duel_policy_id` stamped by the C66 harness.
    Only the final checkpoint's RETAINED IB signs are read, not summed over
    checkpoints (the same sign persists and could be reused or overwritten).
    """
    indexed, errors = {}, []
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"malformed_jsonl_line_{line_no}")
                continue
            if not isinstance(row, dict):
                errors.append(f"non_object_jsonl_line_{line_no}")
                continue
            run = row.get("run")
            if not isinstance(run, list) or not run or run[0] != "OpexAI":
                continue
            if len(run) != 3 or nonnegative(run[1]) is None or nonnegative(run[2]) is None:
                errors.append(f"malformed_run_key_line_{line_no}")
                continue
            policy = row.get("duel_policy_id")
            if not isinstance(policy, str) or not policy:
                errors.append(f"missing_policy_line_{line_no}")
                continue
            indexed.setdefault((policy, run[1], run[2]), []).append(row)
    return indexed, errors


def extract_ib_proxy(last, first_year, last_year):
    """Retained IB B<n> = successful portfolio pass count of *unknown mode*.

    Not total historical builds, not physical net lines, not air/rail-specific:
    SIGN panels can be absent, overwritten or pruned, and B includes fleet.
    """
    total = nonnegative(last.get("project_builds_sign_total"))
    parsed = nonnegative(last.get("project_build_signs_parsed"))
    yearly = last.get("project_builds_sign_by_year")
    if total is None or parsed is None or not isinstance(yearly, dict):
        return {"status": "missing", "retained_total": None, "retained_by_year": None,
                "panels_parsed": None}
    annual = {}
    for year, value in yearly.items():
        if not isinstance(year, str) or not year.isdigit() or not first_year <= int(year) <= last_year:
            return {"status": "invalid_year", "retained_total": None,
                    "retained_by_year": None, "panels_parsed": parsed}
        amount = nonnegative(value)
        if amount is None:
            return {"status": "invalid_count", "retained_total": None,
                    "retained_by_year": None, "panels_parsed": parsed}
        annual[year] = amount
    if sum(annual.values()) != total:
        return {"status": "inconsistent_total", "retained_total": None,
                "retained_by_year": None, "panels_parsed": parsed}
    if parsed == 0:
        return {"status": "no_retained_panels", "retained_total": None,
                "retained_by_year": None, "panels_parsed": parsed}
    return {"status": "retained_sign_proxy_only", "retained_total": total,
            "retained_by_year": annual, "panels_parsed": parsed}


def checkpoint_evidence(rows, *, last_date, years, bundle, game_id):
    if rows is None:
        return {"status": "not_available", "issues": ["jsonl_missing_for_arm"],
                "monthly_stock_changes": None, "retained_ib_project_pass_proxy": None}
    issues = []
    rows = sorted(rows, key=lambda row: str(row.get("date", "")))
    dates = [row.get("date") for row in rows]
    expected = years * 12
    if len(dates) != expected:
        issues.append("monthly_checkpoint_count_mismatch")
    if len(set(dates)) != len(dates):
        issues.append("duplicate_monthly_checkpoint")
    if any(not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
           for date in dates):
        issues.append("checkpoint_dates_invalid")
    if (not dates or not isinstance(dates[0], str) or dates[0][:7] != "1970-01"
            or dates[-1] != last_date):
        issues.append("checkpoint_boundaries_mismatch")
    expected_months = [f"{year}-{month:02d}" for year in range(1970, 1970 + years)
                       for month in range(1, 13)]
    if [date[:7] if isinstance(date, str) else None for date in dates] != expected_months:
        issues.append("checkpoint_monthly_calendar_mismatch")
    if any(row.get("game_id") != game_id or row.get("source_bundle_sha256") != bundle
           for row in rows):
        issues.append("checkpoint_identity_mismatch")
    changes = {}
    for label, (outer, mode, validity) in CHECKPOINT_FIELDS.items():
        series = []
        for row in rows:
            group = row.get(outer)
            value = (nonnegative(group.get(mode)) if row.get(validity) is True
                     and isinstance(group, dict) else None)
            series.append(value)
        observed_pairs = [(index, prev, current)
                          for index, (prev, current) in enumerate(zip(series, series[1:]), 1)
                          if prev is not None and current is not None]
        positive = [(index, new - old) for index, old, new in observed_pairs if new > old]
        negative = [(index, old - new) for index, old, new in observed_pairs if new < old]
        changes[label] = {
            "complete_monthly_decode": len(observed_pairs) == expected - 1,
            "first_stock": series[0] if series else None,
            "final_stock": series[-1] if series else None,
            "positive_change_months": len(positive),
            "net_positive_stock_deltas_sum": sum(delta for _, delta in positive),
            "negative_change_months": len(negative),
            "net_negative_stock_deltas_sum": sum(delta for _, delta in negative),
            "months_since_positive_stock_change": len(series) - 1 - positive[-1][0] if positive else None,
        }
        if len(observed_pairs) != expected - 1:
            issues.append(f"monthly_{label}_decode_incomplete")
    ib = extract_ib_proxy(rows[-1], 1970, 1970 + years - 1) if rows else None
    if ib is not None and ib["status"] in ("invalid_year", "invalid_count", "inconsistent_total"):
        issues.append("retained_ib_panel_inconsistent")
    return {"status": "complete" if not issues else "incomplete", "issues": issues,
            "monthly_stock_changes": changes, "retained_ib_project_pass_proxy": ib}


def validated_physical(row, mode, problems):
    """Facility counts overlap in multimodal stations and must not be summed."""
    physical = row.get("physical_ok") is True
    qualified = row.get("qualified_modes")
    if not isinstance(qualified, dict) or qualified.get(mode) is not True:
        problems.append(f"unqualified_mode_{mode}")
        return {"vehicles": None, "stations": None}
    vehicles = None
    if physical and row.get("vehs_chunk_valid") is True:
        modes = row.get("primary_vehicles_by_mode")
        vehicles = nonnegative(modes.get(mode)) if isinstance(modes, dict) else None
    stations = None
    if physical and row.get("stnn_chunk_valid") is True:
        facilities = row.get("stations_by_facility")
        stations = nonnegative(facilities.get(FACILITIES[mode])) if isinstance(facilities, dict) else None
    if vehicles is None:
        problems.append(f"missing_or_invalid_vehicles_{mode}")
    if stations is None:
        problems.append(f"missing_or_invalid_stations_{mode}")
    return {"vehicles": vehicles, "stations": stations}


def company_evidence(row, game, expected_last_year, expected_checkpoints):
    issues, warnings = [], []
    expected_conditions = {"run_ok": True, "game_ok": True, "horizon_complete": True,
                           "physical_ok": True, "vehs_chunk_valid": True,
                           "stnn_chunk_valid": True}
    for field, required in expected_conditions.items():
        if row.get(field) is not required:
            issues.append(f"{field}_not_true")
    if row.get("status") != "complete":
        issues.append("status_not_complete")
    if game is None or game.get("game_ok") is not True or game.get("game_status") != "complete":
        issues.append("duel_game_not_complete")
    if row.get("last_year") != expected_last_year:
        issues.append("horizon_last_year_mismatch")
    if row.get("n_savegames") != expected_checkpoints:
        issues.append("savegame_count_mismatch")
    if row.get("profit_year_coverage") != "complete" or row.get("profit_year_quarters_valid") != 4:
        issues.append("profit_year_incomplete")
    if row.get("months_of_bankruptcy") is None or nonnegative(row.get("months_of_bankruptcy")) is None:
        issues.append("bankruptcy_data_missing")
    elif row["months_of_bankruptcy"] > 0:
        warnings.append("bankruptcy_months_positive")
    for field in ("script_errors", "unattributed_errors"):
        value = row.get(field) if field == "script_errors" else (game or {}).get(field)
        if value is None:
            warnings.append(f"{field}_unavailable")
        elif isinstance(value, (list, dict, str)) and len(value) > 0:
            issues.append(f"{field}_nonempty")
        elif type(value) is int and value != 0:
            issues.append(f"{field}_nonzero")
    metrics = {}
    for field in METRICS:
        metrics[field] = (finite_number(row.get(field)) if field in ("profit_year", "company_value")
                          else nonnegative(row.get(field)))
        if metrics[field] is None:
            issues.append(f"missing_or_invalid_{field}")
    activity = row.get("activity")
    activity_result = {}
    if not isinstance(activity, dict):
        activity = {}
        issues.append("activity_missing")
    for field in ACTIVITY:
        activity_result[field] = nonnegative(activity.get(field))
        if activity_result[field] is None:
            warnings.append(f"activity_{field}_unavailable")
    activity_result["signal"] = activity.get("signal") if isinstance(activity.get("signal"), str) else None
    activity_result["n_checkpoints"] = nonnegative(activity.get("n_checkpoints"))
    if activity_result["n_checkpoints"] != expected_checkpoints:
        warnings.append("activity_checkpoints_incomplete")
    # These counts are transitions of *stocks* over monthly checkpoints.
    # A change may be due to construction, demolition, vehicle replacement etc.
    gap = activity_result["months_since_fleet_or_network_change"]
    if gap is not None and gap >= 24:
        warnings.append("no_fleet_or_station_stock_change_in_last_24_months")
    if activity_result["signal"] in (None, "no_signal", "declining_without_expansion"):
        warnings.append("weak_recent_activity_signal")
    physical = {mode: validated_physical(row, mode, issues) for mode in MODES}
    return {"healthy": not issues, "issues": sorted(set(issues)),
            "warnings": sorted(set(warnings)), "metrics": metrics,
            "physical_final_stocks": physical, "activity_checkpoint_deltas": activity_result}


def summarize_pairs(data, *, reference_policy="reference", variant_policy="p0_topk_binary",
                    expected_seeds=20, expected_years=10, expected_bundle_prefix=None,
                    checkpoints=None, checkpoint_errors=None):
    if not isinstance(data, dict):
        raise ValueError("C66 root must be an object")
    for key in ("summary", "games", "seeds", "policies"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"C66 {key} must be an array")
    issues = []
    if data.get("years") != expected_years:
        issues.append("campaign_years_mismatch")
    if data.get("repeats") != 1:
        issues.append("campaign_repeats_not_one")
    seeds = data["seeds"]
    if any(nonnegative(seed) is None for seed in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("C66 seeds must be distinct nonnegative integers")
    if len(seeds) != expected_seeds:
        issues.append("campaign_seed_count_mismatch")
    bundle = data.get("source_bundle_sha256")
    if not isinstance(bundle, str) or not bundle:
        issues.append("bundle_missing")
    if expected_bundle_prefix and (not isinstance(bundle, str) or not bundle.startswith(expected_bundle_prefix)):
        issues.append("bundle_mismatch")
    if checkpoint_errors:
        issues.extend(checkpoint_errors)
    roles = {p.get("role"): p.get("id") for p in data["policies"] if isinstance(p, dict)}
    if roles.get("reference") != reference_policy or roles.get("variant") != variant_policy:
        issues.append("policy_roles_mismatch")
    indexes, game_index = {}, {}
    for row in data["summary"]:
        ident = seed_repeat(row)
        if ident is None:
            issues.append("malformed_summary_identity")
            continue
        if row.get("arm") != "OpexAI":
            continue
        key = (row.get("duel_policy_id"), *ident)
        indexes.setdefault(key, []).append(row)
    for game in data["games"]:
        ident = seed_repeat(game)
        if ident is None:
            issues.append("malformed_game_identity")
            continue
        game_index.setdefault((game.get("policy_id"), *ident), []).append(game)
    records = []
    for seed in sorted(seeds):
        for repeat in range(1):
            pair_issues = []
            arms = {}
            for name, policy in (("reference", reference_policy), ("variant", variant_policy)):
                key = (policy, seed, repeat)
                rows, games = indexes.get(key, []), game_index.get(key, [])
                if len(rows) != 1:
                    pair_issues.append(f"{name}_summary_count_{len(rows)}")
                if len(games) != 1:
                    pair_issues.append(f"{name}_game_count_{len(games)}")
                if len(rows) != 1:
                    arms[name] = None
                    continue
                row = rows[0]
                game = games[0] if len(games) == 1 else None
                if row.get("policy_id") != policy:
                    pair_issues.append(f"{name}_policy_identity_mismatch")
                if row.get("source_bundle_sha256") != bundle:
                    pair_issues.append(f"{name}_bundle_identity_mismatch")
                if game is not None and (game.get("source_bundle_sha256") != bundle
                                         or game.get("game_id") != row.get("game_id")):
                    pair_issues.append(f"{name}_game_identity_mismatch")
                arms[name] = company_evidence(row, game, 1970 + expected_years - 1,
                                              expected_years * 12)
                cp = (checkpoint_evidence(checkpoints.get(key), last_date=data.get("expected_last_checkpoint"),
                                          years=expected_years, bundle=bundle, game_id=row.get("game_id"))
                      if checkpoints is not None else None)
                arms[name]["checkpoints"] = cp
                if cp is not None and cp["status"] != "complete":
                    pair_issues.extend(f"{name}_{issue}" for issue in cp["issues"])
                if cp is not None and cp["monthly_stock_changes"] is not None:
                    for mode in MODES:
                        for label, stock_type in ((f"{mode}_vehicles", "vehicles"),
                                                  ("airports" if mode == "air" else "rail_stations", "stations")):
                            observed = cp["monthly_stock_changes"][label]["final_stock"]
                            reported = arms[name]["physical_final_stocks"][mode][stock_type]
                            if observed is not None and reported is not None and observed != reported:
                                pair_issues.append(f"{name}_{label}_checkpoint_final_stock_conflict")
            ref, var = arms.get("reference"), arms.get("variant")
            valid = (not pair_issues and ref is not None and var is not None
                     and ref["healthy"] and var["healthy"])
            paired = {field: pair_delta(ref["metrics"].get(field), var["metrics"].get(field))
                      if ref and var else None for field in METRICS}
            for mode in MODES:
                for field in ("vehicles", "stations"):
                    label = f"{mode}_{field}_final_stock"
                    paired[label] = (pair_delta(ref["physical_final_stocks"][mode][field],
                                                var["physical_final_stocks"][mode][field])
                                     if ref and var else None)
            for field in ACTIVITY:
                paired[f"checkpoint_{field}"] = (
                    pair_delta(ref["activity_checkpoint_deltas"][field],
                               var["activity_checkpoint_deltas"][field])
                    if ref and var else None)
            warnings = [f"{name}:{warning}" for name, arm in arms.items() if arm is not None
                        for warning in arm["warnings"]]
            checkpoint_deltas = {}
            for label in CHECKPOINT_FIELDS:
                for field in ("positive_change_months", "net_positive_stock_deltas_sum",
                              "negative_change_months", "net_negative_stock_deltas_sum"):
                    left = (ref.get("checkpoints") or {}).get("monthly_stock_changes") if ref else None
                    right = (var.get("checkpoints") or {}).get("monthly_stock_changes") if var else None
                    checkpoint_deltas[f"{label}_{field}"] = (
                        pair_delta(left[label][field], right[label][field]) if left and right else None)
            def ib_for(arm):
                return ((arm.get("checkpoints") or {}).get("retained_ib_project_pass_proxy")
                        if arm is not None else None)
            ib_ref, ib_var = ib_for(ref), ib_for(var)
            ib_ref_n = ib_ref.get("retained_total") if ib_ref else None
            ib_var_n = ib_var.get("retained_total") if ib_var else None
            records.append({"seed": seed, "repeat": repeat, "valid_pair": valid,
                            "issues": pair_issues, "warnings": sorted(set(warnings)),
                            "reference": ref, "variant": var, "variant_minus_reference": paired,
                            "checkpoint_stock_change_deltas": checkpoint_deltas,
                            "retained_ib_project_pass_proxy": {
                                "reference": ib_ref, "variant": ib_var,
                                "delta_retained_total": pair_delta(ib_ref_n, ib_var_n),
                                "status": "incomplete_or_unavailable" if ib_ref_n is None or ib_var_n is None else
                                          "observed_retained_signs_not_total_builds"},
                            "line_builds_air_rail": {
                                "reference": None, "variant": None, "delta": None,
                                "status": "not_measured_by_this_C66_summary",
                            }})
    unexpected = sorted(k for k in indexes if k[0] in (reference_policy, variant_policy)
                        and (k[1] not in seeds or k[2] != 0))
    if unexpected:
        issues.append("unexpected_opex_summary_identities")
    missing_pairs = [(r["seed"], r["repeat"]) for r in records if not r["valid_pair"]]
    deltas = {field: [r["variant_minus_reference"][field] for r in records
                      if r["valid_pair"] and r["variant_minus_reference"][field] is not None]
              for field in (*METRICS, "air_vehicles_final_stock", "rail_vehicles_final_stock",
                            "air_stations_final_stock", "rail_stations_final_stock")}
    aggregates = {field: {"paired_n": len(vals), "mean_variant_minus_reference":
                          sum(vals) / len(vals) if vals else None,
                          "worse": sum(x < 0 for x in vals), "better": sum(x > 0 for x in vals),
                          "equal": sum(x == 0 for x in vals)}
                  for field, vals in deltas.items()}
    trend_aggregates = {}
    for label in CHECKPOINT_FIELDS:
        for field in ("positive_change_months", "net_positive_stock_deltas_sum",
                      "negative_change_months", "net_negative_stock_deltas_sum"):
            name = f"{label}_{field}"
            values = [row["checkpoint_stock_change_deltas"][name] for row in records
                      if row["valid_pair"] and row["checkpoint_stock_change_deltas"][name] is not None]
            trend_aggregates[name] = {"paired_n": len(values),
                                      "mean_variant_minus_reference":
                                      sum(values) / len(values) if values else None}
    alert_count = sum(bool(r["warnings"]) for r in records)
    checkpoint_complete = sum(r["reference"] is not None and r["variant"] is not None
                              and (r["reference"].get("checkpoints") or {}).get("status") == "complete"
                              and (r["variant"].get("checkpoints") or {}).get("status") == "complete"
                              for r in records)
    proxies = [r["retained_ib_project_pass_proxy"]["delta_retained_total"] for r in records
               if r["retained_ib_project_pass_proxy"]["delta_retained_total"] is not None]
    qa = {"expected_pairs": expected_seeds, "observed_pairs": len(records),
          "valid_pairs": len(records) - len(missing_pairs), "invalid_pairs": missing_pairs,
          "campaign_issues": issues, "pairs_with_activity_warnings": alert_count,
          "pairwise_health_complete": not issues and not missing_pairs and len(records) == expected_seeds,
          "complete_monthly_checkpoint_pairs": checkpoint_complete,
          "monthly_checkpoints_available": checkpoints is not None,
          "retained_ib_proxy_paired_n": len(proxies),
          "retained_ib_proxy_mean_delta": sum(proxies) / len(proxies) if proxies else None,
          "non_famine_indirect_screen": ("not_assessable" if issues or missing_pairs else
                                        "review_activity_warnings" if alert_count else
                                        "no_health_or_stagnation_warning_detected"),
          "strict_non_famine_certified": False,
          "strict_non_famine_reason": "C66 final physical stocks and monthly-change counters do not record AIR/RAIL line builds or their survival timeline",
          "line_build_coverage": "unavailable",
          "next_qa": ["Verify 20 paired seeds, full 1979-12 checkpoint, per-arm health and physical decode.",
                      "Review per-mode monthly stock rises and falls: counts reflect net stock changes, not new lines.",
                      "Retained IB B<n> counts successful portfolio projects of unknown mode; signs can be overwritten and are not a complete build history.",
                      "Inspect AIR/RAIL opening/closing events in explicitly collected line telemetry before claiming construction continuity.",
                      "Inspect warning pairs, economic outcomes, and game trajectory; stock deltas do not prove causal effect."]}
    return {"campaign_id": data.get("campaign_id"), "bundle": bundle,
            "source": "C66 summary and games JSON, plus optional monthly JSONL (no line event telemetry)",
            "reference_policy": reference_policy, "variant_policy": variant_policy,
            "qa": qa, "aggregates": aggregates,
            "monthly_stock_trend_aggregates": trend_aggregates, "per_seed": records}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66_json", type=Path)
    p.add_argument("--reference-policy", default="reference")
    p.add_argument("--variant-policy", default="p0_topk_binary")
    p.add_argument("--expected-seeds", type=int, default=20)
    p.add_argument("--expected-years", type=int, default=10)
    p.add_argument("--expected-bundle-prefix", default="def46d63")
    p.add_argument("--jsonl", type=Path, help="Optional C66 checkpoint JSONL, auto-discovered beside JSON")
    p.add_argument("--no-jsonl", action="store_true", help="Disable checkpoint analysis")
    p.add_argument("--summary-only", action="store_true")
    p.add_argument("--out", type=Path, help="Optional new output file; omitted by default")
    p.add_argument("--fail-on-qa", action="store_true")
    args = p.parse_args(argv)
    try:
        cp_file = None if args.no_jsonl else (args.jsonl or args.c66_json.with_suffix(".jsonl"))
        if args.jsonl is not None and not args.jsonl.is_file():
            p.error(f"explicit checkpoint JSONL not found: {args.jsonl}")
        checkpoints, checkpoint_errors = (load_checkpoints(cp_file) if cp_file and cp_file.is_file()
                                           else (None, []))
        result = summarize_pairs(json.loads(args.c66_json.read_text(encoding="utf-8")),
                                 reference_policy=args.reference_policy,
                                 variant_policy=args.variant_policy,
                                 expected_seeds=args.expected_seeds,
                                 expected_years=args.expected_years,
                                 expected_bundle_prefix=args.expected_bundle_prefix,
                                 checkpoints=checkpoints, checkpoint_errors=checkpoint_errors)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    if args.out is not None:
        if args.out.exists():
            p.error("refusing to overwrite an existing report")
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    view = {k: result[k] for k in ("campaign_id", "bundle", "source", "qa", "aggregates",
                                   "monthly_stock_trend_aggregates")} if args.summary_only else result
    print(json.dumps(view, indent=2, ensure_ascii=False))
    return 2 if args.fail_on_qa and not result["qa"]["pairwise_health_complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
